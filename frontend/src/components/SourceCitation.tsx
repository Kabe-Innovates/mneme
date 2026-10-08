import { useState } from "react";
import { ChevronDown, ChevronUp, FileText, Network } from "lucide-react";
import type { Source, GraphNode } from "../types";
import { clsx } from "clsx";

interface Props {
  sources: Source[];
  graphContext?: GraphNode[];
}

const nodeTypeColors: Record<string, string> = {
  Team: "bg-purple-100 text-purple-700",
  System: "bg-cyan-100 text-cyan-700",
  Field: "bg-amber-100 text-amber-700",
  Step: "bg-green-100 text-green-700",
  Workflow: "bg-blue-100 text-blue-700",
  Role: "bg-slate-100 text-slate-600",
  Form: "bg-orange-100 text-orange-700",
};

export function SourceCitation({ sources, graphContext = [] }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasGraph = graphContext.length > 0;

  if (!sources.length && !hasGraph) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
      >
        <FileText className="h-3.5 w-3.5" />
        <span>{sources.length} source{sources.length !== 1 ? "s" : ""} cited</span>
        {hasGraph && (
          <>
            <span className="text-slate-300">·</span>
            <Network className="h-3.5 w-3.5 text-blue-400" />
            <span className="text-blue-500">{graphContext.length} graph nodes</span>
          </>
        )}
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {expanded && (
        <div className="mt-2 space-y-2">
          {/* Source documents */}
          {sources.length > 0 && (
            <div className="flex flex-wrap gap-2">
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

          {/* Knowledge graph context */}
          {hasGraph && (
            <div>
              <p className="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-400">
                <Network className="h-3 w-3" />
                Knowledge Graph — connected entities
              </p>
              <div className="flex flex-wrap gap-1.5">
                {graphContext.map((node) => (
                  <div
                    key={node.node_id}
                    className="flex items-center gap-1 rounded-full border border-slate-100 bg-white px-2 py-0.5"
                    title={node.detail || node.node_id}
                  >
                    <span
                      className={clsx(
                        "rounded-full px-1.5 py-0.5 text-xs font-semibold",
                        nodeTypeColors[node.node_type] || "bg-slate-100 text-slate-600"
                      )}
                    >
                      {node.node_type}
                    </span>
                    <span className="text-xs text-slate-700">{node.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
