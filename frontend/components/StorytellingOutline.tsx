"use client";

import { useState } from "react";
import { Pencil, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import SlideCard from "@/components/SlideCard";
import type { StorytellingOutline as OutlineType, Slide } from "@/lib/types";

interface StorytellingOutlineProps {
  outline: OutlineType;
  onChange: (outline: OutlineType) => void;
}

export default function StorytellingOutline({
  outline,
  onChange,
}: StorytellingOutlineProps) {
  const [editable, setEditable] = useState(false);

  const handleSlideChange = (idx: number, slide: Slide) => {
    const slides = [...outline.slides];
    slides[idx] = slide;
    onChange({ ...outline, slides });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold tracking-tight text-foreground">
            {outline.title}
          </h2>
          <p className="text-sm text-muted-foreground">
            {outline.objective}
          </p>
          <p className="text-xs text-muted-foreground">
            Audiencia: {outline.audience} &middot; {outline.total_slides} slides
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setEditable(!editable)}
          aria-label={editable ? "Visualizar outline" : "Editar outline"}
          className="shrink-0 gap-1.5"
        >
          {editable ? (
            <>
              <Eye className="h-3.5 w-3.5" />
              Visualizar
            </>
          ) : (
            <>
              <Pencil className="h-3.5 w-3.5" />
              Editar
            </>
          )}
        </Button>
      </div>

      <div className="space-y-3">
        {outline.slides.map((slide, idx) => (
          <SlideCard
            key={slide.index}
            slide={slide}
            editable={editable}
            onChange={(s) => handleSlideChange(idx, s)}
          />
        ))}
      </div>
    </div>
  );
}
