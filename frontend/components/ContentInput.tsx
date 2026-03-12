"use client";

import { useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MAX_CHARS = 5000;
const WARN_THRESHOLD = 4800;

interface ContentInputProps {
  value: string;
  onChange: (value: string) => void;
}

export default function ContentInput({ value, onChange }: ContentInputProps) {
  const charCount = value.length;
  const isWarning = charCount >= WARN_THRESHOLD;
  const isOver = charCount > MAX_CHARS;

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      <Textarea
        value={value}
        onChange={handleChange}
        maxLength={MAX_CHARS}
        placeholder="Descreva o que voce quer apresentar. Pode ser informal — a IA vai estruturar o storytelling para voce."
        data-testid="content-input"
      aria-label="Conteudo da apresentacao"
        className={cn(
          "min-h-[200px] resize-y bg-secondary text-foreground placeholder:text-muted-foreground",
          "focus-visible:ring-[var(--indigo)]",
          isWarning && !isOver && "border-amber-500 focus-visible:ring-amber-500",
          isOver && "border-destructive focus-visible:ring-destructive"
        )}
      />
      <div className="flex justify-end">
        <span
          className={cn(
            "text-xs tabular-nums",
            isOver
              ? "text-destructive"
              : isWarning
                ? "text-amber-500"
                : "text-muted-foreground"
          )}
          aria-live="polite"
          data-testid={isOver ? "content-error" : undefined}
        >
          {charCount}/{MAX_CHARS}
        </span>
      </div>
    </div>
  );
}
