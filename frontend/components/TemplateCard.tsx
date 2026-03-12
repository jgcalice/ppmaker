"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Template } from "@/lib/types";

interface TemplateCardProps {
  template: Template;
  selected: boolean;
  onClick: () => void;
}

const PALETTE_KEYS = ["primary", "secondary", "accent", "background", "text"] as const;

export default function TemplateCard({
  template,
  selected,
  onClick,
}: TemplateCardProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      data-testid="template-card"
      aria-label={`Selecionar template ${template.name}`}
      aria-pressed={selected}
      className={cn(
        "group relative flex flex-col gap-4 rounded-xl border p-5 text-left transition-colors",
        "bg-card hover:border-[var(--indigo)]/50",
        selected
          ? "border-[var(--indigo)] ring-1 ring-[var(--indigo)]"
          : "border-border"
      )}
    >
      {selected && (
        <div className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--indigo)]">
          <Check className="h-3.5 w-3.5 text-white" />
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold tracking-tight text-foreground">
          {template.name}
        </h3>
        <Badge
          variant="outline"
          className="shrink-0 text-[10px] uppercase tracking-wider"
        >
          {template.scope}
        </Badge>
      </div>

      <div className="flex items-center gap-1.5">
        {PALETTE_KEYS.map((key) => (
          <span
            key={key}
            className="h-4 w-4 rounded-full border border-white/10"
            style={{ backgroundColor: template.palette[key] }}
            aria-label={`Cor ${key}: ${template.palette[key]}`}
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-1">
        {template.layouts.slice(0, 3).map((layout) => (
          <Badge key={layout} variant="secondary" className="text-[10px]">
            {layout}
          </Badge>
        ))}
        {template.layouts.length > 3 && (
          <Badge variant="secondary" className="text-[10px]">
            +{template.layouts.length - 3}
          </Badge>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        {template.font_title} / {template.font_body}
      </p>
    </motion.button>
  );
}
