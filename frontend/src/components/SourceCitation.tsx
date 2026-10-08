import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import type { Source } from "../types";

interface Props {
  sources: Source[];
}

export function SourceCitation({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!sources.length) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
      >
        <FileText className="h-3.5 w-3.5" />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""} cited</span>
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {expanded && (
        <div className="mt-2 flex flex-wrap gap-2">
          {sources.map((src) => (
            <div
              key={src.source_id}
              className="flex items-center gap-1.5 rounded-md bg-blue-50 border border-blue-100 px-2.5 py-1.5"
            >
              <span className="font-mono text-xs font-semibold text-blue-700">
                {src.source_id}
              </span>
              <span className="text-xs text-slate-600">{src.title}</span>
              {src.department && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                  {src.department}
                </span>
              )}
              <span className="text-xs text-slate-400">
                {Math.round(src.relevance * 100)}% match
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
