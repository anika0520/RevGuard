"use client";

import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { api, fetcher } from "@/lib/api";
import type { CampaignRow, Incident } from "@/lib/types";

export function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (v: boolean) => void }) {
  const router = useRouter();
  const { data: campaigns } = useSWR<CampaignRow[]>(open ? "/api/campaigns?sort=risk&limit=40" : null, fetcher);
  const { data: incidents } = useSWR<Incident[]>(open ? "/api/incidents?active_only=true&limit=20" : null, fetcher);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setOpen(false);
    try {
      await fn();
      toast.success(label);
    } catch {
      toast.error(`${label} failed`);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[120] flex items-start justify-center pt-[12vh]">
      <div className="absolute inset-0 bg-fg/25 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <Command
        className="relative z-10 w-full max-w-xl overflow-hidden rounded-xl border border-line bg-surface shadow-pop"
        loop
      >
        <Command.Input
          autoFocus
          placeholder="Search campaigns and incidents, or run an action…"
          className="w-full border-b border-line bg-transparent px-4 py-3.5 text-sm text-fg outline-none placeholder:text-subtle"
        />
        <Command.List className="max-h-[55vh] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-xs text-subtle">No matches.</Command.Empty>

          <Command.Group heading="Actions" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-widest [&_[cmdk-group-heading]]:text-subtle">
            <Item onSelect={() => act("Replaying the Acme cascade", () => api.replayGolden())}>
              Replay reference incident
            </Item>
            <Item onSelect={() => act("Analysis complete", () => api.runAnalysis())}>Run full analysis</Item>
            <Item onSelect={() => act("Injected VAST spike", () => api.simInject("vast_spike"))}>Inject VAST error spike</Item>
            <Item onSelect={() => act("Injected data outage", () => api.simInject("data_outage"))}>Inject data feed outage</Item>
            <Item onSelect={() => act("World reset", () => api.simReset())}>Reset simulated world</Item>
          </Command.Group>

          <Command.Group heading="Navigate" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-widest [&_[cmdk-group-heading]]:text-subtle">
            <Item onSelect={() => go("/")}>Mission Control</Item>
            <Item onSelect={() => go("/campaigns")}>Campaign Health</Item>
            <Item onSelect={() => go("/incidents")}>Incident Center</Item>
            <Item onSelect={() => go("/impact")}>Impact ledger</Item>
            <Item onSelect={() => go("/agent")}>Agent trace</Item>
            <Item onSelect={() => go("/settings")}>Settings</Item>
          </Command.Group>

          {incidents?.length ? (
            <Command.Group heading="Open incidents" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-widest [&_[cmdk-group-heading]]:text-subtle">
              {incidents.slice(0, 8).map((i) => (
                <Item key={i.incident_id} onSelect={() => go(`/campaigns/${i.campaign_id}`)}>
                  <span className="text-subtle">{i.incident_id}</span> {i.campaign_name}
                  <span className="ml-auto text-2xs text-danger">{i.severity}</span>
                </Item>
              ))}
            </Command.Group>
          ) : null}

          {campaigns?.length ? (
            <Command.Group heading="Campaigns" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-widest [&_[cmdk-group-heading]]:text-subtle">
              {campaigns.slice(0, 12).map((c) => (
                <Item key={c.campaign_id} onSelect={() => go(`/campaigns/${c.campaign_id}`)}>
                  {c.campaign_name}
                  <span className="ml-auto text-2xs text-subtle">{c.campaign_id}</span>
                </Item>
              ))}
            </Command.Group>
          ) : null}
        </Command.List>
      </Command>
    </div>
  );
}

function Item({ children, onSelect }: { children: React.ReactNode; onSelect: () => void }) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-muted aria-selected:bg-elevated aria-selected:text-fg"
    >
      {children}
    </Command.Item>
  );
}
