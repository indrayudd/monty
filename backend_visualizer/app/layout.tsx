import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { TopAppBar } from "./components/TopAppBar";

export const metadata: Metadata = {
  title: "Monty Backend Visualizer",
  description:
    "Live visualization of the agent loop: behavioral KG, per-student timeline, wiki browser, and console.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-black text-white antialiased">
        <TopAppBar />
        {children}
      </body>
    </html>
  );
}
