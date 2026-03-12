"""
visual_director.py
------------------
Visual Director service for PPMaker.

Consumes a layout_catalog.json (produced by tools/inspect_template.py) and
brand_tokens.json, then:

  1. Selects the best stencil layout for each slide based on content signals.
  2. Generates a full SlideSpec (a structured rendering contract) either via
     Claude claude-sonnet-4-6 or a deterministic fallback.

The SlideSpec tells the StencilRenderer exactly what text to put where, how to
style it, and what quality checks to run.

Usage (from StencilRenderer or directly):
    vd = VisualDirector(catalog_path, brand_tokens_path, api_key=None)
    layout_id = vd.select_layout(slide_content, deck_context)
    entry = vd.get_catalog_entry(layout_id)
    spec = vd.generate_spec(slide_content, deck_context, entry)
"""

import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for the Claude visual-director call
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are the Visual Director for a premium PowerPoint generation system (PPMaker).
Your role: given a slide's content signals and a concrete stencil layout entry,
produce a SlideSpec JSON that tells the renderer exactly what to write where.

INPUTS you will receive (as JSON):
  - slide_content  : { layout_hint, title, bullets, has_placeholder }
  - deck_context   : { deck_title, audience, tone, slide_index, total_slides }
  - layout_catalog_entry : the selected stencil entry (features, text_zones, image_zones, use_for)
  - brand_tokens   : { palette, typography }

RULES:
1. headline: The title, rewritten to be punchy and ≤ 8 words. No full stop.
2. headline_highlight: Identify one power word/phrase in the headline to
   visually emphasise (mode="word" for single word, "phrase" for 2-3 words,
   "none" if no emphasis needed).
3. takeaway: A single crisp sentence (≤ 15 words) summarising the slide's
   message. Starts with an action verb or key stat.
4. placeholders: Map each text_zone zone_id to the content string to place
   there. Use role hints (TITLE, SUBTITLE, BODY, HIGHLIGHT, LABEL, CAPTION).
   HIGHLIGHT and LABEL zones must keep their original decorative content
   (return them with value "__KEEP__").
5. visuals.icons: suggest 1-3 Lucide icon names (string slugs) relevant to
   the slide topic. Only if the layout has roundRect cards.
6. visuals.images: leave empty unless slide_content has explicit image signals.
7. visuals.charts: leave empty unless has_placeholder is True.
8. content_edits: shorten_rules_applied = list any bullet that was shortened.
   rewrites = list {original, rewritten} pairs if you rewrote bullets.
9. quality_checks.max_objects_ok: True if text_zones <= 8.
10. quality_checks.text_overflow_risk: "low" if total chars < 400, "medium"
    < 800, "high" otherwise.
11. quality_checks.notes: any important caveats for the renderer.

OUTPUT: valid JSON only, exactly matching this schema:
{
  "layout_id": "SLIDEXX",
  "headline": "...",
  "headline_highlight": {"text": "...", "mode": "word|phrase|none"},
  "takeaway": "...",
  "placeholders": { "ZONE_0": "...", "ZONE_1": "..." },
  "visuals": { "icons": [], "images": [], "charts": [] },
  "content_edits": { "shorten_rules_applied": [], "rewrites": [] },
  "quality_checks": {
    "max_objects_ok": true,
    "text_overflow_risk": "low",
    "notes": []
  }
}
Do NOT output markdown fences or any text outside the JSON object.
""".strip()


# ---------------------------------------------------------------------------
# VisualDirector
# ---------------------------------------------------------------------------

class VisualDirector:
    """
    Selects stencil layouts and generates SlideSpec contracts for slides.

    Parameters
    ----------
    catalog_path : str
        Path to layout_catalog.json (produced by inspect_template.py).
    brand_tokens_path : str
        Path to brand_tokens.json.
    api_key : str | None
        Anthropic API key. If None, all specs use the deterministic fallback.
    """

    def __init__(
        self,
        catalog_path: str,
        brand_tokens_path: str,
        api_key: str | None = None,
    ) -> None:
        self.api_key = api_key

        # Load catalog
        try:
            with open(catalog_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._catalog: list[dict] = raw.get("catalog", [])
        except Exception as exc:
            logger.warning("Could not load catalog from %s: %s", catalog_path, exc)
            self._catalog = []

        # Load brand tokens
        try:
            with open(brand_tokens_path, "r", encoding="utf-8") as fh:
                self._brand_tokens: dict = json.load(fh)
        except Exception as exc:
            logger.warning("Could not load brand tokens from %s: %s", brand_tokens_path, exc)
            self._brand_tokens = {}

        # Build reverse index: use_for tag → list of catalog entries
        self._use_for_index: dict[str, list[dict]] = {}
        for entry in self._catalog:
            for tag in entry.get("use_for", []):
                self._use_for_index.setdefault(tag, []).append(entry)

        logger.info(
            "VisualDirector loaded %d catalog entries, %d use_for tags",
            len(self._catalog),
            len(self._use_for_index),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_layout(self, slide_content: dict, deck_context: dict) -> str:
        """
        Choose the best stencil layout_id for a slide.

        Parameters
        ----------
        slide_content : dict
            Keys: layout_hint (str), title (str), bullets (list[str]),
                  has_placeholder (bool).
        deck_context : dict
            Keys: deck_title, audience, tone, slide_index, total_slides.

        Returns
        -------
        str
            layout_id such as "SLIDE04".
        """
        hint = slide_content.get("layout_hint", "content").lower()

        # Try exact hint match
        candidates = self._use_for_index.get(hint, [])

        # For two-column, merge two-column + content-only candidates so we can
        # score among all plausible layouts (avoids being locked into 3-column cards)
        if hint == "two-column":
            content_only = self._use_for_index.get("content", [])
            seen_ids = {e["layout_id"] for e in candidates}
            candidates = candidates + [e for e in content_only if e["layout_id"] not in seen_ids]

        # For image-text and hero, expand pool to all slides with >= 2 image zones
        # (catalog may not explicitly tag them, but scoring will prefer them)
        if hint in ("image-text", "hero"):
            image_rich = [e for e in self._catalog if len(e.get("image_zones", [])) >= 2]
            seen_ids = {e["layout_id"] for e in candidates}
            candidates = candidates + [e for e in image_rich if e["layout_id"] not in seen_ids]

        # Try alias mapping
        if not candidates:
            aliases = {
                "hero":             ["hero", "title"],
                "section":          ["title", "section"],
                "cards":            ["cards"],
                "dashboard":        ["dashboard", "chart-placeholder"],
                "chart-placeholder":["chart-placeholder", "dashboard"],
                "image-text":       ["image-text", "hero"],
                "team":             ["team"],
                "closing":          ["closing"],
                "two-column":       ["two-column", "content"],
            }
            for alias_tag in aliases.get(hint, ["content"]):
                candidates = self._use_for_index.get(alias_tag, [])
                if candidates:
                    break

        # Fallback to "content"
        if not candidates:
            candidates = self._use_for_index.get("content", [])

        # Robust fallback: always prefer layouts with compatible TITLE + BODY zones
        if not candidates:
            candidates = [e for e in self._catalog if self._has_required_text_roles(e)]
        else:
            compatible = [e for e in candidates if self._has_required_text_roles(e)]
            if compatible:
                candidates = compatible

        if not candidates:
            # Absolute fallback: first slide in catalog
            return self._catalog[0]["layout_id"] if self._catalog else "SLIDE02"

        # Score candidates by feature relevance
        best = self._pick_with_variety(candidates, slide_content, deck_context)
        return best["layout_id"]

    def generate_spec(
        self,
        slide_content: dict,
        deck_context: dict,
        layout_catalog_entry: dict,
    ) -> dict:
        """
        Generate a full SlideSpec for a slide.

        Tries the Claude API when api_key is set; falls back to deterministic
        logic on any failure.
        """
        if self.api_key:
            try:
                return self._llm_spec(slide_content, deck_context, layout_catalog_entry)
            except Exception as exc:
                logger.warning("LLM spec failed (%s), using fallback.", exc)

        return self._fallback_spec(slide_content, deck_context, layout_catalog_entry)

    def get_stencil_index(self, layout_id: str) -> int | None:
        """
        Return the 0-based slide_index in the stencil PPTX for the given layout_id.
        Returns None if not found.
        """
        entry = self.get_catalog_entry(layout_id)
        if entry is None:
            return None
        return entry.get("slide_index")

    def get_catalog_entry(self, layout_id: str) -> dict | None:
        """Return the catalog entry dict for a layout_id, or None."""
        for entry in self._catalog:
            if entry["layout_id"] == layout_id:
                return entry
        return None

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_candidates(self, candidates: list[dict], slide_content: dict) -> dict:
        """
        Rank candidate catalog entries; return the highest-scoring one.

        Scoring criteria:
          +3  has_chart AND slide has has_placeholder
          +2  hero_images_circle > 0 AND layout_hint is hero
          +2  cards_roundrect >= 4 AND n_bullets in [4, 6]
          +1  text_density matches expected range
          -1  heavy slide (text_density > 8) picked for minimal content
        """
        hint = slide_content.get("layout_hint", "content")
        n_bullets = len(slide_content.get("bullets", []))
        has_ph = slide_content.get("has_placeholder", False)

        scored = []
        for entry in candidates:
            feat = entry.get("features", {})
            score = 0

            if has_ph and feat.get("has_chart"):
                score += 3
            if hint in ("hero", "title") and feat.get("hero_images_circle", 0) > 0:
                score += 2
            if 4 <= n_bullets <= 6 and feat.get("cards_roundrect", 0) >= 4:
                score += 2
            td = feat.get("text_density", 0)
            if 2 <= td <= 6 and 1 <= n_bullets <= 5:
                score += 1
            if td > 8 and n_bullets <= 2:
                score -= 1

            # Image richness bonus — HERO_RECT (brand photos) valued much more than DECO shapes
            image_zones = entry.get("image_zones", [])
            hero_rects = sum(1 for z in image_zones if z.get("role") == "HERO_RECT")
            deco_count = sum(1 for z in image_zones if z.get("role") == "DECO")
            score += min(hero_rects * 2, 8)   # up to +8 for brand photos (SLIDE06: 5×2=10→8)
            score += min(deco_count // 3, 2)  # max +2 for decorative shapes

            # Zone count: only penalise text-dense slides with NO brand photos
            n_zones = len(entry.get("text_zones", []))
            if hint in ("content", "two-column", "image-text"):
                if n_zones <= 5 and hero_rects == 0:
                    score += 1   # simple text layout acceptable when no brand photos available
                if n_zones > 10 and hero_rects == 0:
                    score -= 2   # penalise text-dense slides with no visual richness

            scored.append((score, entry))

        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1]

    def _score_candidates_ranked(self, candidates: list[dict], slide_content: dict) -> list[dict]:
        """Return candidates sorted by score desc (used for variety selection)."""
        hint = slide_content.get("layout_hint", "content")
        n_bullets = len(slide_content.get("bullets", []))
        has_ph = slide_content.get("has_placeholder", False)

        scored: list[tuple[int, dict]] = []
        for entry in candidates:
            feat = entry.get("features", {})
            score = 0

            if has_ph and feat.get("has_chart"):
                score += 3
            if hint in ("hero", "title") and feat.get("hero_images_circle", 0) > 0:
                score += 2
            if 4 <= n_bullets <= 6 and feat.get("cards_roundrect", 0) >= 4:
                score += 2
            td = feat.get("text_density", 0)
            if 2 <= td <= 6 and 1 <= n_bullets <= 5:
                score += 1
            if td > 8 and n_bullets <= 2:
                score -= 1

            image_zones = entry.get("image_zones", [])
            hero_rects = sum(1 for z in image_zones if z.get("role") == "HERO_RECT")
            deco_count = sum(1 for z in image_zones if z.get("role") == "DECO")
            score += min(hero_rects * 2, 8)
            score += min(deco_count // 3, 2)

            n_zones = len(entry.get("text_zones", []))
            if hint in ("content", "two-column", "image-text"):
                if n_zones <= 5 and hero_rects == 0:
                    score += 1
                if n_zones > 10 and hero_rects == 0:
                    score -= 2

            # Guarantee required zones are favored in fallback situations
            if self._has_required_text_roles(entry):
                score += 1

            scored.append((score, entry))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [entry for _, entry in scored]

    def _pick_with_variety(self, candidates: list[dict], slide_content: dict, deck_context: dict) -> dict:
        """Pick best layout, increasing variety for long decks."""
        ranked = self._score_candidates_ranked(candidates, slide_content)
        if not ranked:
            return self._score_candidates(candidates, slide_content)

        total_slides = int(deck_context.get("total_slides", 0) or 0)
        slide_index = int(deck_context.get("slide_index", 1) or 1)
        if total_slides < 10 or len(ranked) == 1:
            return ranked[0]

        pool_size = min(4, len(ranked))
        pool = ranked[:pool_size]
        pick_idx = (slide_index - 1) % pool_size
        return pool[pick_idx]

    def _has_required_text_roles(self, entry: dict) -> bool:
        """Check if layout has both TITLE and BODY-compatible text zones."""
        zones = entry.get("text_zones", [])
        if not zones:
            return False

        roles = {str(z.get("role", "")).upper() for z in zones}
        has_title = "TITLE" in roles or "SUBTITLE" in roles
        has_body = "BODY" in roles or "CAPTION" in roles
        return has_title and has_body

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _llm_spec(
        self,
        slide_content: dict,
        deck_context: dict,
        layout_catalog_entry: dict,
    ) -> dict:
        """Call Claude claude-sonnet-4-6 to generate the SlideSpec."""
        try:
            import anthropic  # optional dep — only needed if api_key is set
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed. Install with: pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=self.api_key)

        user_payload = {
            "slide_content":        slide_content,
            "deck_context":         deck_context,
            "layout_catalog_entry": layout_catalog_entry,
            "brand_tokens":         self._brand_tokens,
        }

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role":    "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
        )

        raw = message.content[0].text.strip()

        # Strip accidental markdown fences
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        spec = json.loads(raw)

        # Ensure layout_id is set
        if "layout_id" not in spec:
            spec["layout_id"] = layout_catalog_entry.get("layout_id", "SLIDE02")

        return spec

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------

    def _fallback_spec(
        self,
        slide_content: dict,
        deck_context: dict,
        layout_entry: dict,
    ) -> dict:
        """
        Produce a SlideSpec without an LLM.

        Rules:
          - Bullets 4-6 → cards format (one bullet per card zone)
          - Bullets 1-3 → content format
          - has_placeholder → mark chart zone
          - headline_highlight → longest word in title
          - takeaway → first bullet, or title if no bullets
          - __KEEP__ for decorative HIGHLIGHT / LABEL zones
        """
        layout_id   = layout_entry.get("layout_id", "SLIDE02")
        title       = slide_content.get("title", "")
        bullets     = slide_content.get("bullets", [])
        has_ph      = slide_content.get("has_placeholder", False)
        text_zones  = layout_entry.get("text_zones", [])

        # Headline (trim to 8 words)
        headline_words = title.split()
        headline = " ".join(headline_words[:8])
        if len(headline_words) > 8:
            headline = headline + "…"

        # Highlight word — longest word in headline
        words = [w.strip(".,;:!?") for w in headline.split() if len(w) > 3]
        highlight_text = max(words, key=len) if words else ""
        highlight = {
            "text": highlight_text,
            "mode": "word" if highlight_text else "none",
        }

        # Takeaway
        takeaway = bullets[0] if bullets else title

        # Build placeholders
        placeholders: dict[str, str] = {}
        title_assigned   = False
        subtitle_assigned = False
        body_assigned    = False

        for zone in text_zones:
            zid  = zone["zone_id"]
            role = zone["role"]

            if role in ("HIGHLIGHT", "LABEL"):
                placeholders[zid] = "__KEEP__"
            elif role == "TITLE" and not title_assigned:
                placeholders[zid] = headline
                title_assigned = True
            elif role == "SUBTITLE" and not subtitle_assigned:
                sub = bullets[0] if bullets else ""
                placeholders[zid] = sub
                subtitle_assigned = True
            elif role == "BODY" and not body_assigned:
                # Join bullets as newline-separated text
                placeholders[zid] = "\n".join(bullets)
                body_assigned = True
            elif role == "CAPTION":
                placeholders[zid] = takeaway

        # Icons suggestion (only for card layouts)
        icons: list[str] = []
        feat = layout_entry.get("features", {})
        if feat.get("cards_roundrect", 0) >= 4:
            # Generic icon slugs; renderer can use or ignore
            icons = ["bar-chart-2", "trending-up", "layers", "check-circle"]

        # Chart spec
        charts: list[dict] = []
        if has_ph:
            charts = [{"type": "placeholder", "hint": slide_content.get("placeholder_hint", "")}]

        # Quality checks
        total_chars = len(title) + sum(len(b) for b in bullets)
        if total_chars < 400:
            overflow_risk = "low"
        elif total_chars < 800:
            overflow_risk = "medium"
        else:
            overflow_risk = "high"

        max_objects_ok = len(text_zones) <= 8

        notes: list[str] = []
        if not title_assigned:
            notes.append("No TITLE zone found in stencil; title not placed.")
        if bullets and not body_assigned:
            notes.append("No BODY zone found; bullets not placed.")

        return {
            "layout_id":          layout_id,
            "headline":           headline,
            "headline_highlight": highlight,
            "takeaway":           takeaway,
            "placeholders":       placeholders,
            "visuals": {
                "icons":  icons,
                "images": [],
                "charts": charts,
            },
            "content_edits": {
                "shorten_rules_applied": [],
                "rewrites": [],
            },
            "quality_checks": {
                "max_objects_ok":    max_objects_ok,
                "text_overflow_risk": overflow_risk,
                "notes":             notes,
            },
        }
