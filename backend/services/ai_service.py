import asyncio
import json
import os

import anthropic

from models.schemas import StorytellingOutline
from prompts.storytelling import STORYTELLING_SYSTEM_PROMPT, STORYTELLING_USER_PROMPT


PROGRESS_STEPS = [
    {"step": "planner", "message": "Analisando conteúdo..."},
    {"step": "architect", "message": "Estruturando slides..."},
    {"step": "story_builder", "message": "Construindo narrativa..."},
    {"step": "visual_director", "message": "Definindo layouts..."},
    {"step": "content_gen", "message": "Gerando conteúdo..."},
    {"step": "editor", "message": "Revisando e finalizando..."},
]


async def generate_storytelling(
    content: str,
    template_id: str,
    audience: str | None = None,
    objective: str | None = None,
    tone: str = "professional",
):
    """
    Generator that yields SSE events: progress steps, then the outline, then done.
    Uses a single Claude API call with fake progress events.
    """
    audience = audience or "Público geral"
    objective = objective or "Informar e engajar a audiência"

    prompt = STORYTELLING_USER_PROMPT.format(
        content=content,
        audience=audience,
        objective=objective,
        tone=tone,
    )

    # Start Claude API call in background
    api_task = asyncio.create_task(_call_claude(prompt))

    # Emit progress events with delays while Claude processes
    for i, step_info in enumerate(PROGRESS_STEPS):
        event = {
            "type": "progress",
            "step": step_info["step"],
            "message": step_info["message"],
        }
        yield f"data: {json.dumps(event)}\n\n"

        # Wait between steps; on the last step, wait for the API result
        if i < len(PROGRESS_STEPS) - 1:
            await asyncio.sleep(0.8)
        else:
            # Wait for Claude to finish
            await api_task

    # Get the result
    result_text = api_task.result()

    # Parse the JSON response
    outline = _parse_outline(result_text)

    # Emit the outline
    outline_event = {
        "type": "outline",
        "data": outline.model_dump(),
    }
    yield f"data: {json.dumps(outline_event)}\n\n"

    # Done
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def _call_claude(prompt: str) -> str:
    """Call Claude API and return the text response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    message = await asyncio.wait_for(
        client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=STORYTELLING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ),
        timeout=120,
    )

    return message.content[0].text


def _parse_outline(text: str) -> StorytellingOutline:
    """Parse Claude's response into a StorytellingOutline."""
    # Strip potential markdown code fences
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove first line and last line
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove ```json or ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    data = json.loads(cleaned)
    return StorytellingOutline(**data)
