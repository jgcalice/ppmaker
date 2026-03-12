"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, RefreshCw, LayoutGrid } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import TemplateCard from "@/components/TemplateCard";
import { fetchTemplates } from "@/lib/api";
import type { Template } from "@/lib/types";

export default function TemplatesPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTemplates();
      setTemplates(data.templates);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao carregar templates"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    router.push(`/create?template_id=${id}`);
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/")}
            aria-label="Voltar para home"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <LayoutGrid className="h-5 w-5 text-[var(--indigo)]" />
            <h1 className="text-xl font-bold tracking-tight">Templates</h1>
          </div>
          {!loading && templates.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {templates.length}
            </Badge>
          )}
        </div>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div
          className="flex flex-col items-center gap-4 py-16 text-center"
          role="alert"
        >
          <p className="text-sm text-destructive">{error}</p>
          <Button
            variant="outline"
            onClick={load}
            aria-label="Tentar novamente"
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      )}

      {!loading && !error && templates.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <p className="text-sm text-muted-foreground">
            Nenhum template encontrado.
          </p>
          <Button
            variant="outline"
            onClick={load}
            aria-label="Recarregar templates"
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Recarregar
          </Button>
        </div>
      )}

      {!loading && !error && templates.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
          {templates.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              selected={t.id === selectedId}
              onClick={() => handleSelect(t.id)}
            />
          ))}
        </motion.div>
      )}
    </main>
  );
}
