"use client";

import { ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { AccountNode, Nature } from "@/types/account";

interface Props {
  nodes: AccountNode[];
  selectedCode: string | null;
  onSelect: (account: AccountNode) => void;
  // Open every branch.
  expandAll?: boolean;
}

export function AccountTree({
  nodes,
  selectedCode,
  onSelect,
  expandAll = false,
}: Props) {
  const t = useTranslations("accounts");

  if (nodes.length === 0) {
    return (
      <p className="p-10 text-center text-sm text-muted-foreground">
        {t("empty")}
      </p>
    );
  }

  return (
    <ul className="p-2">
      {nodes.map((node) => (
        <TreeItem
          key={node.code}
          node={node}
          depth={0}
          selectedCode={selectedCode}
          onSelect={onSelect}
          expandAll={expandAll}
        />
      ))}
    </ul>
  );
}

interface ItemProps {
  node: AccountNode;
  depth: number;
  selectedCode: string | null;
  onSelect: (account: AccountNode) => void;
  expandAll: boolean;
}

function TreeItem({
  node,
  depth,
  selectedCode,
  onSelect,
  expandAll,
}: ItemProps) {
  const t = useTranslations("accounts");
  const [expanded, setExpanded] = useState(expandAll || depth === 0);

  const hasChildren = node.children.length > 0;
  const isSelected = node.code === selectedCode;
  const isDeleted = node.deleted_at !== null;

  return (
    <li>
      <div
        className={cn(
          "group flex items-center gap-1 rounded-lg pl-1 pr-2 text-sm transition-colors",
          isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted",
        )}
      >
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className={cn(
            "grid size-5 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors",
            hasChildren ? "hover:bg-foreground/10" : "invisible",
          )}
          aria-label={expanded ? t("collapse") : t("expand")}
          aria-expanded={hasChildren ? expanded : undefined}
        >
          <ChevronRight
            className={cn(
              "size-3.5 transition-transform duration-150",
              expanded && "rotate-90",
            )}
          />
        </button>

        <button
          type="button"
          onClick={() => onSelect(node)}
          className="flex min-w-0 flex-1 items-baseline gap-2 py-1.5 text-left outline-none"
        >
          <span
            className={cn(
              "shrink-0 font-mono text-xs tabular-nums",
              isSelected ? "text-primary/80" : "text-muted-foreground",
            )}
          >
            {node.code}
          </span>
          <span
            className={cn(
              "truncate",
              (isDeleted || !node.is_active) && "line-through opacity-50",
              depth === 0 && "font-medium",
            )}
          >
            {node.name}
          </span>
          {isDeleted && (
            <span className="shrink-0 rounded-md bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-destructive">
              {t("deletedBadge")}
            </span>
          )}
          <NatureBadge nature={node.nature} />
        </button>
      </div>

      {hasChildren && expanded && (
        <ul
          className="ml-[0.85rem] border-l border-border/70"
        >
          {node.children.map((child) => (
            <TreeItem
              key={child.code}
              node={child}
              depth={depth + 1}
              selectedCode={selectedCode}
              onSelect={onSelect}
              expandAll={expandAll}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function NatureBadge({ nature }: { nature: Nature }) {
  const t = useTranslations("nature");
  const isDebit = nature === "Debito";

  return (
    <span
      className={cn(
        "ml-auto shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        isDebit
          ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400"
          : "bg-amber-500/12 text-amber-700 dark:text-amber-400",
      )}
    >
      {t(nature)}
    </span>
  );
}
