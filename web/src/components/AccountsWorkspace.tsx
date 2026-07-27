"use client";

import { Eye, EyeOff, Plus, Search, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo, useState } from "react";

import { AccountForm } from "@/components/AccountForm";
import { AccountTree } from "@/components/AccountTree";
import { ImportForm } from "@/components/ImportForm";
import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AccountNode } from "@/types/account";

type Panel = "form" | "import";

interface Props {
  tree: AccountNode[];
  loadError: string | null;
  showDeleted: boolean;
}

// Only interaction lives on the client: selection, search and which panel is open.
export function AccountsWorkspace({ tree, loadError, showDeleted }: Props) {
  const t = useTranslations("accounts");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("form");
  const [search, setSearch] = useState("");

  const query = search.trim();
  const visible = useMemo(() => filterTree(tree, query), [tree, query]);
  const total = useMemo(() => countNodes(tree), [tree]);
  const shown = useMemo(() => countNodes(visible), [visible]);
  const selected = useMemo(
    () => (selectedCode ? findNode(tree, selectedCode) : null),
    [tree, selectedCode],
  );

  return (
    <PageShell>
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={
          <>
            {t("count", { count: total })}
            {showDeleted && ` · ${t("includingDeleted")}`}
          </>
        }
        actions={
          <>
            <Button
              variant="outline"
              nativeButton={false}
              render={
                <Link href={showDeleted ? "/accounts" : "/accounts?deleted=1"} />
              }
            >
              {showDeleted ? <EyeOff /> : <Eye />}
              {showDeleted ? t("hideDeleted") : t("showDeleted")}
            </Button>
            <Button variant="outline" onClick={() => setPanel("import")}>
              <Upload />
              {t("importSpreadsheet")}
            </Button>
            <Button
              onClick={() => {
                setSelectedCode(null);
                setPanel("form");
              }}
            >
              <Plus />
              {t("newAccount")}
            </Button>
          </>
        }
      />

      {loadError && <LoadError message={loadError} />}

      <div className="grid gap-5 lg:grid-cols-[1fr_23rem] lg:items-start">
        <section className="min-w-0 overflow-hidden rounded-xl bg-card shadow-sm ring-1 ring-border">
          <div className="flex items-center gap-2 border-b border-border p-3">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("searchPlaceholder")}
                className="pl-8"
              />
            </div>
            {query !== "" && (
              <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                {t("matches", { count: shown })}
              </span>
            )}
          </div>

          <div className="scrollbar-slim max-h-[65vh] overflow-y-auto">
            <AccountTree
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

        <aside className="rounded-xl bg-card p-4 shadow-sm ring-1 ring-border lg:sticky lg:top-6">
          {panel === "import" ? (
            <ImportForm />
          ) : (
            <AccountForm
              key={selected?.code ?? "new"}
              account={selected}
              onCancel={() => setSelectedCode(null)}
            />
          )}
        </aside>
      </div>
    </PageShell>
  );
}

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

function findNode(nodes: AccountNode[], code: string): AccountNode | null {
  for (const node of nodes) {
    if (node.code === code) return node;
    const found = findNode(node.children, code);
    if (found) return found;
  }
  return null;
}
