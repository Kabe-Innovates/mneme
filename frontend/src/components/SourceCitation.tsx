import { useState } from "react";
import { ChevronDown, ChevronUp, FileText, Network } from "lucide-react";
import type { Source, GraphNode } from "../types";
import { clsx } from "clsx";

interface Props {
  sources: Source[];
  graphContext?: GraphNode[];
}

const nodeTypeColors: Record<string, string> = {
  Team:     "bg-purple-500/15 text-purple-400",
  System:   "bg-cyan-500/15 text-cyan-400",
  Field:    "bg-amber-500/15 text-amber-400",
  Step:     "bg-green-500/15 text-green-400",
  Workflow: "bg-blue-500/15 text-blue-400",
  Role:     "bg-dark-hover text-dark-muted",
  Form:     "bg-orange-500/15 text-orange-400",
};

export function SourceCitation({ sources, graphContext = [] }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasGraph = graphContext.length > 0;

  if (!sources.length && !hasGraph) return null;

  return (
    <div className="mt-3 border-t border-dark-border pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-dark-muted hover:text-dark-text transition-colors"
      >
        <FileText className="h-3.5 w-3.5" />
        <span>{sources.length} source{sources.length !== 1 ? "s" : ""} cited</span>
        {hasGraph && (
          <>
            <span className="text-dark-border">·</span>
            <Network className="h-3.5 w-3.5 text-brand-400" />
            <span className="text-brand-400">{graphContext.length} graph nodes</span>
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
                  className="flex items-center gap-1.5 rounded-md border border-blue-500/20 bg-blue-500/15 px-2.5 py-1.5"
                >
                  <span className="font-mono text-xs font-semibold text-blue-400">
                    {src.source_id}
                  </span>
                  <span className="text-xs text-dark-text">{src.title}</span>
                  {src.department && (
                    <span className="rounded bg-dark-hover px-1.5 py-0.5 text-xs text-dark-muted">
                      {src.department}
                    </span>
                  )}
                  <span className="text-xs text-dark-muted">
                    {Math.round(src.relevance * 100)}% match
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Knowledge graph context */}
          {hasGraph && (
            <div>
              <p className="mb-1.5 flex items-center gap-1 text-xs font-medium text-dark-muted">
                <Network className="h-3 w-3" />
                Knowledge Graph — connected entities
              </p>
              <div className="flex flex-wrap gap-1.5">
                {graphContext.map((node) => (
                  <div
                    key={node.node_id}
                    className="flex items-center gap-1 rounded-full border border-dark-border bg-dark-surface px-2 py-0.5"
                    title={node.detail || node.node_id}
                  >
                    <span
                      className={clsx(
                        "rounded-full px-1.5 py-0.5 text-xs font-semibold",
                        nodeTypeColors[node.node_type] || "bg-dark-hover text-dark-muted"
                      )}
                    >
                      {node.node_type}
                    </span>
                    <span className="text-xs text-dark-text">{node.title}</span>
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
