"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import type { AccountNode, Nature } from "@/types/account";

interface Props {
  nodes: AccountNode[];
  selectedCode: string | null;
  onSelect: (account: AccountNode) => void;
  /**
   * Open every branch. Set while searching: a match buried under collapsed
   * ancestors would otherwise look like no result at all.
   */
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
    return <p className="p-6 text-sm text-muted">{t("empty")}</p>;
  }

  return (
    <ul className="py-2">
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
  // Classes start open; everything else collapsed, or a 2,446-account tree
  // would be unreadable at a glance. While searching everything opens, and the
  // parent remounts the tree so this initial value is re-evaluated.
  const [expanded, setExpanded] = useState(expandAll || depth === 0);

  const hasChildren = node.children.length > 0;
  const isSelected = node.code === selectedCode;
  const isDeleted = node.deleted_at !== null;

  return (
    <li>
      <div
        className={`flex items-center gap-1 rounded-md pr-2 text-sm transition-colors ${
          isSelected
            ? "bg-accent/15 text-blue-700 dark:text-blue-300"
            : "hover:bg-foreground/5"
        }`}
        style={{ paddingLeft: `${depth * 1.1 + 0.5}rem` }}
      >
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className={`grid size-5 shrink-0 place-items-center rounded text-xs text-muted ${
            hasChildren
              ? "hover:bg-foreground/10"
              : "invisible"
          }`}
          aria-label={expanded ? t("collapse") : t("expand")}
          aria-expanded={hasChildren ? expanded : undefined}
        >
          {expanded ? "▾" : "▸"}
        </button>

        <button
          type="button"
          onClick={() => onSelect(node)}
          className="flex min-w-0 flex-1 items-baseline gap-2 py-1 text-left"
        >
          <span className="shrink-0 font-mono text-xs tabular-nums opacity-70">
            {node.code}
          </span>
          <span
            className={`truncate ${
              isDeleted || !node.is_active ? "line-through opacity-50" : ""
            }`}
          >
            {node.name}
          </span>
          {isDeleted && (
            <span className="shrink-0 rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-red-700 dark:text-red-400">
              {t("deletedBadge")}
            </span>
          )}
          <NatureBadge nature={node.nature} />
        </button>
      </div>

      {hasChildren && expanded && (
        <ul>
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
      className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        isDebit
          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
          : "bg-amber-500/15 text-amber-700 dark:text-amber-400"
      }`}
    >
      {t(nature)}
    </span>
  );
}
