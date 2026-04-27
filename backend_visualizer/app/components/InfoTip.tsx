"use client";

import { useState, useRef, useCallback, useLayoutEffect } from "react";
import { createPortal } from "react-dom";

export default function InfoTip({ text, side = "top" }: { text: string; side?: "top" | "bottom" | "left" | "right" }) {
  const [visible, setVisible] = useState(false);
  const [style, setStyle] = useState<React.CSSProperties>({ position: "fixed", visibility: "hidden", zIndex: 9999 });
  const iconRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);

  const TIP_W = 224;
  const GAP = 6;
  const PAD = 8; // viewport edge padding

  // Two-phase: first render hidden to measure, then position
  useLayoutEffect(() => {
    if (!visible || !iconRef.current || !tipRef.current) return;

    const ir = iconRef.current.getBoundingClientRect();
    const tipH = tipRef.current.offsetHeight;
    const cx = ir.left + ir.width / 2;
    const cy = ir.top + ir.height / 2;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const clampLeft = (l: number) => Math.max(PAD, Math.min(l, vw - TIP_W - PAD));

    type Placement = { top: number; left: number };

    const placements: Record<string, () => Placement | null> = {
      top: () => {
        const t = ir.top - GAP - tipH;
        return t >= PAD ? { top: t, left: clampLeft(cx - TIP_W / 2) } : null;
      },
      bottom: () => {
        const t = ir.bottom + GAP;
        return t + tipH <= vh - PAD ? { top: t, left: clampLeft(cx - TIP_W / 2) } : null;
      },
      left: () => {
        const l = ir.left - GAP - TIP_W;
        return l >= PAD ? { top: Math.max(PAD, Math.min(cy - tipH / 2, vh - tipH - PAD)), left: l } : null;
      },
      right: () => {
        const l = ir.right + GAP;
        return l + TIP_W <= vw - PAD ? { top: Math.max(PAD, Math.min(cy - tipH / 2, vh - tipH - PAD)), left: l } : null;
      },
    };

    const opposite: Record<string, string> = { top: "bottom", bottom: "top", left: "right", right: "left" };
    const order = [side, opposite[side], "bottom", "top", "right", "left"];
    let result: Placement | null = null;
    for (const s of order) {
      result = placements[s]?.() ?? null;
      if (result) break;
    }

    // Last resort: just place below, clamped
    if (!result) {
      result = {
        top: Math.max(PAD, Math.min(ir.bottom + GAP, vh - tipH - PAD)),
        left: clampLeft(cx - TIP_W / 2),
      };
    }

    setStyle({
      position: "fixed",
      zIndex: 9999,
      width: TIP_W,
      top: result.top,
      left: result.left,
      visibility: "visible",
    });
  }, [visible, side, text]);

  const show = useCallback(() => {
    // Reset to hidden so useLayoutEffect can measure fresh
    setStyle({ position: "fixed", visibility: "hidden", zIndex: 9999, width: TIP_W });
    setVisible(true);
  }, []);

  const hide = useCallback(() => {
    setVisible(false);
  }, []);

  return (
    <span
      className="inline-flex items-center ml-1 cursor-help"
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <span
        ref={iconRef}
        className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full border border-zinc-600 text-zinc-500 hover:text-zinc-300 hover:border-zinc-400 transition-colors text-[9px] leading-none select-none"
      >
        i
      </span>
      {visible && typeof document !== "undefined" && createPortal(
        <div
          ref={tipRef}
          style={style}
          className="px-2.5 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-[11px] leading-snug text-zinc-300 shadow-lg pointer-events-none whitespace-normal"
        >
          {text}
        </div>,
        document.body,
      )}
    </span>
  );
}
