"use client";

import { useState } from "react";
import { Loader2, Download, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { downloadPptx } from "@/lib/api";
import type { StorytellingOutline } from "@/lib/types";

interface GenerateButtonProps {
  outline: StorytellingOutline;
  templateId: string;
}

type Status = "idle" | "loading" | "success" | "error";

export default function GenerateButton({
  outline,
  templateId,
}: GenerateButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setStatus("loading");
    setError(null);
    try {
      await downloadPptx({ storytelling: outline, template_id: templateId });
      setStatus("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao gerar apresentacao");
      setStatus("error");
    }
  };

  return (
    <div className="space-y-3">
      <Button
        onClick={handleGenerate}
        disabled={status === "loading"}
        data-testid="generate-pptx-btn"
        aria-label="Gerar apresentacao PowerPoint"
        className="w-full gap-2 bg-[var(--indigo)] text-white hover:bg-[var(--indigo)]/90 disabled:opacity-50"
        size="lg"
      >
        {status === "loading" && (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Gerando...
          </>
        )}
        {status === "idle" && (
          <>
            <Download className="h-4 w-4" />
            Gerar Apresentacao
          </>
        )}
        {status === "success" && (
          <>
            <CheckCircle2 className="h-4 w-4" />
            Baixar PPTX
          </>
        )}
        {status === "error" && (
          <>
            <Download className="h-4 w-4" />
            Tentar Novamente
          </>
        )}
      </Button>
      {error && (
        <p className="text-center text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {status === "success" && (
        <p className="text-center text-sm text-emerald-400">
          Apresentacao gerada com sucesso!
        </p>
      )}
    </div>
  );
}
