"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo, useState } from "react";

import { AccountForm } from "@/components/AccountForm";
import { AccountTree } from "@/components/AccountTree";
import { ImportForm } from "@/components/ImportForm";
import type { AccountNode } from "@/types/account";

type Panel = "form" | "import";

interface Props {
  tree: AccountNode[];
  loadError: string | null;
  showDeleted: boolean;
}

/**
 * Only interaction lives on the client: selection, search and which panel is
 * open. Data arrives already resolved from the server and every mutation goes
 * through a server action.
 */
export function AccountsWorkspace({ tree, loadError, showDeleted }: Props) {
  const t = useTranslations("accounts");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("form");
  const [search, setSearch] = useState("");

  const query = search.trim();
  const visible = useMemo(() => filterTree(tree, query), [tree, query]);
  const total = useMemo(() => countNodes(tree), [tree]);
  const selected = useMemo(
    () => (selectedCode ? findNode(tree, selectedCode) : null),
    [tree, selectedCode],
  );

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("title")}
          </h1>
          <p className="text-sm text-muted">
            {t("count", { count: total })}
            {showDeleted && ` · ${t("includingDeleted")}`}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              setSelectedCode(null);
              setPanel("form");
            }}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground"
          >
            {t("newAccount")}
          </button>
          <button
            type="button"
            onClick={() => setPanel("import")}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            {t("importSpreadsheet")}
          </button>
          <Link
            href={showDeleted ? "/accounts" : "/accounts?deleted=1"}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            {showDeleted ? t("hideDeleted") : t("showDeleted")}
          </Link>
        </div>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {loadError}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <section className="min-w-0 rounded-lg border border-border">
          <div className="border-b border-border p-3">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-full rounded-md border border-border bg-transparent px-3 py-1.5 text-sm"
            />
          </div>

          <div className="max-h-[65vh] overflow-y-auto">
            <AccountTree
              // Remounting on a new query re-evaluates each item's expansion.
              key={query}
              nodes={visible}
              expandAll={query !== ""}
              selectedCode={selectedCode}
              onSelect={(account) => {
                setSelectedCode(account.code);
                setPanel("form");
              }}
            />
          </div>
        </section>

        <aside className="rounded-lg border border-border p-4">
          {panel === "import" ? (
            <ImportForm />
          ) : (
            <AccountForm
              // Remounting on a different account resets the form without effects.
              key={selected?.code ?? "new"}
              account={selected}
              onCancel={() => setSelectedCode(null)}
            />
          )}
        </aside>
      </div>
    </main>
  );
}

/**
 * Prunes the tree down to the branches matching the query.
 * A node survives if it matches or any descendant does, so results are never
 * torn out of their hierarchical context.
 */
function filterTree(nodes: AccountNode[], query: string): AccountNode[] {
  if (!query) return nodes;

  const needle = query.toLowerCase();

  return nodes.flatMap((node) => {
    const children = filterTree(node.children, query);
    const matches =
      node.code.includes(needle) || node.name.toLowerCase().includes(needle);

    if (!matches && children.length === 0) return [];
    return [{ ...node, children }];
  });
}

function countNodes(nodes: AccountNode[]): number {
  return nodes.reduce((total, node) => total + 1 + countNodes(node.children), 0);
}

/** Re-locates the selected account after a revalidation, to avoid stale data. */
function findNode(nodes: AccountNode[], code: string): AccountNode | null {
  for (const node of nodes) {
    if (node.code === code) return node;
    const found = findNode(node.children, code);
    if (found) return found;
  }
  return null;
}
