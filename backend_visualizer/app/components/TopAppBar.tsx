"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function TopAppBar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<string>("Idle");

  useEffect(() => {
    const tick = async () => {
      try {
        const o = (await api.demoOverview()) as {
          runtime?: { mode?: string };
        };
        const mode = o?.runtime?.mode || "idle";
        setStatus(mode.charAt(0).toUpperCase() + mode.slice(1));
      } catch {
        setStatus("Unreachable");
      }
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => clearInterval(i);
  }, []);

  const link = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`px-3 py-1 rounded text-sm ${
          active ? "bg-white/10 text-white" : "text-white/60 hover:text-white"
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
      <div className="font-mono font-semibold tracking-wide text-white">
        monty
      </div>
      <nav className="flex gap-1">
        {link("/", "Live")}
        {link("/wiki", "Wiki")}
        {link("/console", "Console")}
      </nav>
      <div className="ml-auto flex items-center gap-2 text-xs text-white/80 font-mono">
        <span className={`w-2 h-2 rounded-full ${statusColor}`} />
        <span>{status}</span>
      </div>
    </header>
  );
}
