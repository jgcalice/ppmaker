"use client";

import { useState, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import ContentInput from "@/components/ContentInput";
import StorytellingOutline from "@/components/StorytellingOutline";
import GenerateButton from "@/components/GenerateButton";
import ProgressSteps from "@/components/ProgressSteps";
import { streamStorytelling } from "@/lib/api";
import type {
  StorytellingOutline as OutlineType,
  SSEEvent,
} from "@/lib/types";

const STEPS = ["Conteudo", "Contexto", "Storytelling", "Apresentacao"] as const;

const AI_STEPS = [
  "planner",
  "architect",
  "story_builder",
  "visual_director",
  "content_gen",
  "editor",
];

const TONES = [
  { value: "professional" as const, label: "Profissional" },
  { value: "casual" as const, label: "Casual" },
  { value: "executive" as const, label: "Executivo" },
];

function CreatePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const templateId = searchParams.get("template_id") ?? "";

  const [step, setStep] = useState(0);
  const [content, setContent] = useState("");
  const [audience, setAudience] = useState("");
  const [objective, setObjective] = useState("");
  const [tone, setTone] = useState<"professional" | "casual" | "executive">(
    "professional"
  );
  const [outline, setOutline] = useState<OutlineType | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [currentAIStep, setCurrentAIStep] = useState<string | null>(null);
  const [completedAISteps, setCompletedAISteps] = useState<Set<string>>(
    new Set()
  );

  const abortRef = useRef<AbortController | null>(null);

  const canNext =
    (step === 0 && content.trim().length > 0) ||
    step === 1 ||
    (step === 2 && outline !== null) ||
    step === 3;

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setGenError(null);
    setCurrentAIStep(null);
    setCompletedAISteps(new Set());
    setOutline(null);

    abortRef.current = new AbortController();

    try {
      await streamStorytelling(
        {
          content,
          template_id: templateId,
          audience: audience || undefined,
          objective: objective || undefined,
          tone,
        },
        (event: SSEEvent) => {
          if (event.type === "progress") {
            setCurrentAIStep((prev) => {
              if (prev && prev !== event.step) {
                setCompletedAISteps((s) => new Set([...s, prev]));
              }
              return event.step;
            });
          } else if (event.type === "outline") {
            setOutline(event.data);
          } else if (event.type === "done") {
            setCurrentAIStep((prev) => {
              if (prev) {
                setCompletedAISteps((s) => new Set([...s, prev]));
              }
              return null;
            });
          }
        },
        abortRef.current.signal
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setGenError(
          err instanceof Error ? err.message : "Erro ao gerar storytelling"
        );
      }
    } finally {
      setGenerating(false);
    }
  }, [content, templateId, audience, objective, tone]);

  const goNext = () => {
    if (step === 1) {
      handleGenerate();
      setStep(2);
    } else if (step < STEPS.length - 1) {
      setStep(step + 1);
    }
  };

  const goBack = () => {
    if (step > 0) {
      if (step === 2 && abortRef.current) {
        abortRef.current.abort();
      }
      setStep(step - 1);
    } else {
      router.push("/");
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      {/* Top progress bar */}
      <nav className="mb-10 flex items-center gap-1 text-sm" aria-label="Etapas">
        {STEPS.map((label, idx) => (
          <div key={label} className="flex items-center gap-1">
            {idx > 0 && (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )}
            <button
              onClick={() => idx < step && setStep(idx)}
              disabled={idx >= step}
              className={
                idx === step
                  ? "font-semibold text-foreground"
                  : idx < step
                    ? "cursor-pointer text-[var(--indigo)] hover:underline"
                    : "text-muted-foreground"
              }
              aria-current={idx === step ? "step" : undefined}
            >
              {label}
            </button>
          </div>
        ))}
      </nav>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {/* Step 0: Content */}
          {step === 0 && (
            <div className="space-y-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold tracking-tight">Conteudo</h2>
                <p className="text-sm text-muted-foreground">
                  Descreva o que voce quer apresentar.
                </p>
              </div>
              {templateId && (
                <Badge variant="outline" className="gap-1.5">
                  Template: {templateId}
                </Badge>
              )}
              <ContentInput value={content} onChange={setContent} />
            </div>
          )}

          {/* Step 1: Context */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold tracking-tight">Contexto</h2>
                <p className="text-sm text-muted-foreground">
                  Informacoes adicionais para personalizar a apresentacao.
                </p>
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label
                    htmlFor="audience"
                    className="text-sm font-medium text-foreground"
                  >
                    Audiencia
                  </label>
                  <Input
                    id="audience"
                    data-testid="audience-input"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    placeholder="Ex: Diretoria, equipe tecnica, investidores..."
                    className="bg-secondary focus-visible:ring-[var(--indigo)]"
                  />
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="objective"
                    className="text-sm font-medium text-foreground"
                  >
                    Objetivo
                  </label>
                  <Input
                    id="objective"
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    placeholder="Ex: Aprovar budget, apresentar resultados Q4..."
                    className="bg-secondary focus-visible:ring-[var(--indigo)]"
                  />
                </div>
                <div className="space-y-2">
                  <span className="text-sm font-medium text-foreground">
                    Tom
                  </span>
                  <div className="flex gap-2" role="radiogroup" aria-label="Tom da apresentacao">
                    {TONES.map((t) => (
                      <button
                        key={t.value}
                        role="radio"
                        aria-checked={tone === t.value}
                        onClick={() => setTone(t.value)}
                        className={
                          tone === t.value
                            ? "rounded-lg border border-[var(--indigo)] bg-[var(--indigo)]/10 px-4 py-2 text-sm font-medium text-[var(--indigo)]"
                            : "rounded-lg border border-border bg-secondary px-4 py-2 text-sm text-muted-foreground hover:border-[var(--indigo)]/50 transition-colors"
                        }
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Storytelling */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold tracking-tight">
                  Storytelling
                </h2>
                <p className="text-sm text-muted-foreground">
                  A IA esta estruturando sua apresentacao.
                </p>
              </div>

              {(generating || currentAIStep || completedAISteps.size > 0) && (
                <ProgressSteps
                  steps={AI_STEPS}
                  currentStep={currentAIStep}
                  completedSteps={completedAISteps}
                />
              )}

              {generating && !outline && (
                <div className="flex items-center justify-center gap-2 py-12">
                  <Loader2 className="h-5 w-5 animate-spin text-[var(--indigo)]" />
                  <span className="text-sm text-muted-foreground">
                    Gerando storytelling...
                  </span>
                </div>
              )}

              {genError && (
                <div
                  className="flex flex-col items-center gap-4 py-12 text-center"
                  role="alert"
                >
                  <p className="text-sm text-destructive">{genError}</p>
                  <Button
                    variant="outline"
                    onClick={handleGenerate}
                    aria-label="Tentar novamente"
                    className="gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Tentar novamente
                  </Button>
                </div>
              )}

              {outline && (
                <StorytellingOutline outline={outline} onChange={setOutline} />
              )}
            </div>
          )}

          {/* Step 3: Generate */}
          {step === 3 && outline && (
            <div className="space-y-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold tracking-tight">
                  Apresentacao
                </h2>
                <p className="text-sm text-muted-foreground">
                  Gere e baixe sua apresentacao PowerPoint.
                </p>
              </div>

              <div className="rounded-lg border border-border bg-card p-6 space-y-3">
                <h3 className="font-semibold text-foreground">
                  {outline.title}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {outline.total_slides} slides &middot; {outline.audience}
                </p>
              </div>

              <GenerateButton outline={outline} templateId={templateId} />
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation buttons */}
      <div className="mt-10 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={goBack}
          aria-label="Voltar"
          className="gap-1.5"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Button>
        {step < STEPS.length - 1 && (
          <Button
            onClick={goNext}
            disabled={!canNext || (step === 2 && generating)}
            data-testid={step === 1 ? "generate-storytelling-btn" : "next-step-btn"}
            aria-label="Proximo passo"
            className="gap-1.5 bg-[var(--indigo)] text-white hover:bg-[var(--indigo)]/90"
          >
            {step === 1 ? "Gerar Storytelling" : "Proximo"}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </main>
  );
}

export default function CreatePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <CreatePageInner />
    </Suspense>
  );
}
