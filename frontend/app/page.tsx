"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import TemplateCard from "@/components/TemplateCard";
import { fetchTemplates } from "@/lib/api";
import type { Template } from "@/lib/types";

export default function HomePage() {
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
      setError(err instanceof Error ? err.message : "Erro ao carregar templates");
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
    <main className="mx-auto max-w-5xl px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2 mb-12"
      >
        <div className="flex items-center gap-3">
          <Sparkles className="h-6 w-6 text-[var(--indigo)]" />
          <h1 className="text-3xl font-bold tracking-tight">PPMaker</h1>
        </div>
        <p className="text-muted-foreground max-w-lg">
          Transforme texto em apresentacoes profissionais. Selecione um template
          para comecar.
        </p>
      </motion.div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center gap-4 py-16 text-center" role="alert">
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
          <Button variant="outline" onClick={load} aria-label="Recarregar templates" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Recarregar
          </Button>
        </div>
      )}

      {!loading && !error && templates.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
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
