"use client";

import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Slide } from "@/lib/types";

interface SlideCardProps {
  slide: Slide;
  editable: boolean;
  onChange: (slide: Slide) => void;
}

const LAYOUT_COLORS: Record<string, string> = {
  title: "bg-[var(--indigo)]/20 text-[var(--indigo)]",
  content: "bg-emerald-500/20 text-emerald-400",
  "two-column": "bg-sky-500/20 text-sky-400",
  "chart-placeholder": "bg-amber-500/20 text-amber-400",
  "image-text": "bg-purple-500/20 text-purple-400",
  closing: "bg-rose-500/20 text-rose-400",
};

export default function SlideCard({ slide, editable, onChange }: SlideCardProps) {
  const updateTitle = (title: string) => onChange({ ...slide, title });

  const updatePoint = (idx: number, text: string) => {
    const points = [...slide.talking_points];
    points[idx] = text;
    onChange({ ...slide, talking_points: points });
  };

  return (
    <div data-testid="slide-card" className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-secondary text-xs font-bold text-muted-foreground">
          {slide.index}
        </span>
        <Badge
          className={cn(
            "text-[10px] uppercase tracking-wider border-0",
            LAYOUT_COLORS[slide.layout] ?? "bg-secondary text-muted-foreground"
          )}
        >
          {slide.layout}
        </Badge>
        {slide.has_placeholder && (
          <Badge variant="outline" className="gap-1 border-amber-500/50 text-amber-400 text-[10px]">
            <AlertTriangle className="h-3 w-3" />
            Placeholder
          </Badge>
        )}
      </div>

      {editable ? (
        <Input
          value={slide.title}
          onChange={(e) => updateTitle(e.target.value)}
          aria-label={`Titulo do slide ${slide.index}`}
          className="bg-secondary text-foreground focus-visible:ring-[var(--indigo)]"
        />
      ) : (
        <h4 className="text-sm font-semibold text-foreground">{slide.title}</h4>
      )}

      <ul className="space-y-1.5 pl-1">
        {slide.talking_points.map((point, idx) => (
          <li key={idx} className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--indigo)]" />
            {editable ? (
              <Input
                value={point}
                onChange={(e) => updatePoint(idx, e.target.value)}
                aria-label={`Ponto ${idx + 1} do slide ${slide.index}`}
                className="h-auto bg-transparent px-0 py-0.5 text-sm text-muted-foreground focus-visible:ring-[var(--indigo)]"
              />
            ) : (
              <span className="text-sm text-muted-foreground">{point}</span>
            )}
          </li>
        ))}
      </ul>

      {slide.has_placeholder && slide.placeholder_hint && (
        <p className="text-xs italic text-amber-400/70">
          Dica: {slide.placeholder_hint}
        </p>
      )}
    </div>
  );
}
