"use client";

import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { SWRConfig } from "swr";
import { Toaster } from "sonner";
import { fetcher } from "@/lib/api";
import { CommandPalette } from "./CommandPalette";
import { ControlBar } from "./ControlBar";
import { Copilot } from "./Copilot";
import { TopNav } from "./TopNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <SWRConfig value={{ fetcher, revalidateOnFocus: false, keepPreviousData: true }}>
        <div className="flex min-h-screen flex-col">
          <TopNav onOpenPalette={() => setPaletteOpen(true)} />
          <ControlBar />
          <main className="mx-auto w-full max-w-[1600px] flex-1 px-6 py-6">{children}</main>
          <footer className="border-t border-line bg-surface">
            <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-4 gap-y-1 px-6 py-3 text-2xs text-subtle">
              <span>RevGuard</span>
              <span>·</span>
              <span>Deterministic analytics with an evidence-grounded AI layer</span>
              <span>·</span>
              <span>All figures derived from a simulated dataset</span>
            </div>
          </footer>
        </div>
        <CommandPalette open={paletteOpen} setOpen={setPaletteOpen} />
        <Copilot />
        <Toaster
          position="bottom-center"
          toastOptions={{
            className: "!border !border-line !bg-surface !text-fg !shadow-pop !rounded-md",
          }}
        />
      </SWRConfig>
    </ThemeProvider>
  );
}
