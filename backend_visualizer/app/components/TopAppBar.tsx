"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function TopAppBar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<string>("Idle");
  const [utc, setUtc] = useState<string>("");

  useEffect(() => {
    const tick = async () => {
      try {
        const o = (await api.demoOverview()) as {
          runtime?: { mode?: string; last_cycle_at?: string };
        };
        const mode = o?.runtime?.mode || "idle";
        const lastCycle = o?.runtime?.last_cycle_at;
        let label = mode.charAt(0).toUpperCase() + mode.slice(1);
        if (lastCycle) {
          const ageMs = Date.now() - new Date(lastCycle).getTime();
          if (ageMs < 30_000 && label === "Idle") label = "Running";
        }
        setStatus(label);
      } catch {
        setStatus("Unreachable");
      }
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => clearInterval(i);
  }, []);

  // UTC clock, updated every second
  useEffect(() => {
    const fmt = () => {
      const d = new Date();
      setUtc(
        d.getUTCHours().toString().padStart(2, "0") +
          ":" +
          d.getUTCMinutes().toString().padStart(2, "0") +
          ":" +
          d.getUTCSeconds().toString().padStart(2, "0") +
          " UTC",
      );
    };
    fmt();
    const i = setInterval(fmt, 1000);
    return () => clearInterval(i);
  }, []);

  const link = (href: string, label: string, goldWhenActive = false) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`px-3 py-1 rounded text-sm ${
          active
            ? goldWhenActive
              ? "bg-amber-400/10 text-amber-400"
              : "bg-white/10 text-white"
            : "text-white/60 hover:text-white"
        }`}
      >
        {label}
      </Link>
    );
  };

  const statusColor =
    status === "Running"
      ? "bg-emerald-500"
      : status === "Idle"
        ? "bg-zinc-500"
        : status === "Resetting"
          ? "bg-amber-500"
          : status === "Stopped"
            ? "bg-rose-500"
            : "bg-zinc-700";

  return (
    <header className="h-12 border-b border-white/10 bg-black flex items-center px-4 gap-4 shrink-0">
      <div className="font-sans font-bold tracking-wide text-white text-sm">
        MONTY
      </div>
      <nav className="flex gap-1">
        {link("/", "Live")}
        {link("/wiki", "Wiki")}
        {link("/console", "Console")}
        {link("/god-mode", "God Mode", true)}
      </nav>
      <div className="ml-auto flex items-center gap-4 text-xs text-white/80 font-mono">
        <span className="text-white/50">{utc}</span>
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span>{status}</span>
        </span>
      </div>
    </header>
  );
}
