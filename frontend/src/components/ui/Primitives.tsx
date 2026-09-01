"use client";

import { Info } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

/** Every computed figure carries the formula that produced it. */
export function Explain({ text, className }: { text: string; className?: string }) {
  return (
    <span className={cn("group relative inline-flex align-middle", className)}>
      <Info className="h-3.5 w-3.5 cursor-help text-subtle transition-colors group-hover:text-accent" />
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-72 -translate-x-1/2 rounded-md border border-line bg-surface p-3 text-xs font-normal leading-relaxed text-muted opacity-0 shadow-pop transition-opacity duration-150 group-hover:opacity-100">
        {text}
      </span>
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-elevated", className)} />;
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
      <p className="text-sm font-medium text-fg">{title}</p>
      {hint ? <p className="max-w-sm text-xs text-subtle">{hint}</p> : null}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}) {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-fg/25 backdrop-blur-[2px]" onClick={onClose} />
      <div
        className={cn(
          "relative z-10 flex max-h-[85vh] w-full flex-col overflow-hidden rounded-lg border border-line bg-surface shadow-pop",
          wide ? "max-w-4xl" : "max-w-2xl"
        )}
      >
        <div className="border-b border-line px-5 py-4">
          <h3 className="text-sm font-semibold text-fg">{title}</h3>
          {subtitle ? <p className="mt-1 text-xs text-muted">{subtitle}</p> : null}
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-line bg-elevated px-5 py-3">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: string[];
  active: string;
  onChange: (t: string) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-line bg-elevated p-0.5">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={cn(
            "rounded px-3 py-1 text-xs font-medium transition-colors",
            active === t ? "bg-surface text-fg shadow-card" : "text-muted hover:text-fg"
          )}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

export function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
      {hint ? <p className="mt-1 text-sm text-muted">{hint}</p> : null}
    </div>
  );
}
