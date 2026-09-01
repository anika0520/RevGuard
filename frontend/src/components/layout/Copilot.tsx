"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, ChevronDown, Send, Sparkles, Terminal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ToolCall } from "@/lib/types";

type Message = {
  role: "user" | "guardian";
  text: string;
  trace?: ToolCall[];
};

const SUGGESTIONS = [
  "What is my biggest revenue risk right now?",
  "Why is Acme Sports CTV underdelivering?",
  "How much revenue have we protected?",
  "Which platform has the worst VAST errors?",
];

export function Copilot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "guardian",
      text: "I read live monitoring state. Ask me about risk, root causes, or recovered revenue — every answer shows the tools I called.",
    },
  ]);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const ask = async (question: string) => {
    if (!question.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = (await api.ask(question)) as { answer: string; trace: ToolCall[] };
      setMessages((m) => [...m, { role: "guardian", text: res.answer, trace: res.trace }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "guardian", text: "I could not reach the RevGuard API. Is the backend running on :8000?" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.18 }}
            className="fixed bottom-24 right-6 z-50 flex h-[540px] w-[400px] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-pop backdrop-blur"
          >
            <div className="flex items-center gap-2 border-b border-line px-4 py-3">
              <Sparkles className="h-4 w-4 text-success" />
              <div className="leading-tight">
                <p className="text-sm font-semibold text-fg">RevGuard Copilot</p>
                <p className="text-2xs text-subtle">Answers from live state · tool-traced</p>
              </div>
              <button onClick={() => setOpen(false)} className="ml-auto text-subtle hover:text-muted">
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
                  <div
                    className={
                      m.role === "user"
                        ? "max-w-[85%] rounded-2xl rounded-br-sm bg-accent/15 px-3.5 py-2 text-sm text-accent"
                        : "max-w-[92%] rounded-2xl rounded-bl-sm border border-line bg-elevated px-3.5 py-2.5 text-sm leading-relaxed text-fg"
                    }
                  >
                    {m.text}
                    {m.trace?.length ? (
                      <details className="mt-2 border-t border-line pt-2">
                        <summary className="flex cursor-pointer items-center gap-1.5 text-2xs uppercase tracking-wider text-subtle hover:text-muted">
                          <Terminal className="h-3 w-3" /> {m.trace.length} tool call(s)
                        </summary>
                        <div className="mt-1.5 space-y-1">
                          {m.trace.map((t, j) => (
                            <div key={j} className="flex items-center gap-2 font-mono text-2xs text-muted">
                              <span className={t.ok ? "text-success" : "text-danger"}>{t.ok ? "✓" : "✗"}</span>
                              <span className="text-accent">{t.name}</span>
                              <span className="ml-auto tabular-nums text-subtle">{t.duration_ms}ms</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    ) : null}
                  </div>
                </div>
              ))}
              {busy ? <p className="text-xs text-subtle">Querying live state…</p> : null}
              <div ref={bottom} />
            </div>

            <div className="border-t border-line px-3 py-2">
              <div className="mb-2 flex flex-wrap gap-1">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="rounded-full border border-line px-2 py-1 text-2xs text-muted transition-colors hover:border-success/40 hover:text-success"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  ask(input);
                }}
                className="flex items-center gap-2 rounded-lg border border-line bg-elevated px-3 py-2"
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about any campaign…"
                  className="flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-subtle"
                />
                <button type="submit" disabled={busy} className="text-muted hover:text-success disabled:opacity-40">
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent shadow-raised transition-transform hover:scale-105"
        aria-label="Open RevGuard Copilot"
      >
        <Bot className="h-5 w-5 text-white" />
      </button>
    </>
  );
}
