import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Monty Backend Visualizer",
  description: "Live visualization of note ingestion, agent cycles, personality graph growth, and knowledge graph expansion.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
