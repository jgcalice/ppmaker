"use client";

import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProgressStepsProps {
  steps: string[];
  currentStep: string | null;
  completedSteps: Set<string>;
}

const STEP_LABELS: Record<string, string> = {
  planner: "Planejamento",
  architect: "Arquitetura",
  story_builder: "Storytelling",
  visual_director: "Visual",
  content_gen: "Conteudo",
  editor: "Edicao",
};

export default function ProgressSteps({
  steps,
  currentStep,
  completedSteps,
}: ProgressStepsProps) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto py-2" role="progressbar" aria-label="Progresso da geracao de storytelling">
      {steps.map((step, idx) => {
        const isCompleted = completedSteps.has(step);
        const isCurrent = step === currentStep;
        return (
          <div key={step} className="flex items-center gap-2">
            {idx > 0 && (
              <div
                className={cn(
                  "h-px w-6 shrink-0",
                  isCompleted ? "bg-[var(--indigo)]" : "bg-border"
                )}
              />
            )}
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors",
                isCompleted && "bg-[var(--indigo)]/20 text-[var(--indigo)]",
                isCurrent && "bg-[var(--indigo)]/10 text-[var(--indigo)] ring-1 ring-[var(--indigo)]/50",
                !isCompleted && !isCurrent && "bg-secondary text-muted-foreground"
              )}
            >
              {isCompleted && <Check className="h-3 w-3" />}
              {isCurrent && <Loader2 className="h-3 w-3 animate-spin" />}
              {STEP_LABELS[step] ?? step}
            </div>
          </div>
        );
      })}
    </div>
  );
}
