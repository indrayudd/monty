"use client";

import { SuggestionsResponse } from "../lib/api";

export default function Suggestions({
  data,
}: {
  data: SuggestionsResponse;
}) {
  const suggestions = data.suggestions
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">Suggestions</h2>

      <div className="flex-1 space-y-3">
        {suggestions.map((suggestion, i) => (
          <div
            key={i}
            className="bg-gray-800/60 border border-gray-700 rounded-lg p-4"
          >
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-900/50 border border-blue-700 text-blue-300 text-xs flex items-center justify-center">
                {i + 1}
              </span>
              <p className="text-sm text-gray-200 leading-relaxed">
                {suggestion}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 bg-gray-800/40 border border-gray-700/50 rounded-lg p-3">
        <div className="text-xs text-gray-500">
          Severity:{" "}
          <span
            className={
              data.severity === "red"
                ? "text-red-400"
                : data.severity === "yellow"
                ? "text-yellow-400"
                : "text-green-400"
            }
          >
            {data.severity.toUpperCase()}
          </span>
          {" | "}
          Trend:{" "}
          <span className="text-gray-300">{data.trend}</span>
        </div>
      </div>
    </div>
  );
}
