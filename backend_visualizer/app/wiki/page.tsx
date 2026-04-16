"use client";
import { useState } from "react";
import { WikiFileTree } from "../components/WikiFileTree";
import { WikiPageRenderer } from "../components/WikiPageRenderer";
import { WikiBacklinks } from "../components/WikiBacklinks";

export default function WikiPage() {
  const [path, setPath] = useState<string | null>("index.md");
  return (
    <div className="h-[calc(100vh-3rem)] flex">
      <WikiFileTree selected={path} onSelect={setPath} />
      <WikiPageRenderer path={path} onNavigate={setPath} />
      <WikiBacklinks path={path} />
    </div>
  );
}
