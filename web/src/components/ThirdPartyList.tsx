"use client";

import { useTranslations } from "next-intl";

import type { ThirdParty } from "@/types/third-party";

interface Props {
  thirdParties: ThirdParty[];
  selectedId: number | null;
  onSelect: (thirdParty: ThirdParty) => void;
}

export function ThirdPartyList({ thirdParties, selectedId, onSelect }: Props) {
  const t = useTranslations("thirdParties");

  if (thirdParties.length === 0) {
    return <p className="p-6 text-center text-sm text-muted">{t("empty")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="sticky top-0 bg-surface text-xs uppercase tracking-wide text-muted">
        <tr>
          <th className="px-3 py-2 font-medium">{t("columnDocument")}</th>
          <th className="px-3 py-2 font-medium">{t("columnName")}</th>
          <th className="hidden px-3 py-2 font-medium sm:table-cell">
            {t("columnType")}
          </th>
        </tr>
      </thead>
      <tbody>
        {thirdParties.map((thirdParty) => {
          const selected = thirdParty.id === selectedId;
          const deleted = thirdParty.deleted_at !== null;

          return (
            <tr
              key={thirdParty.id}
              onClick={() => onSelect(thirdParty)}
              aria-selected={selected}
              className={`cursor-pointer border-t border-border transition-colors ${
                selected ? "bg-accent/10" : "hover:bg-foreground/5"
              }`}
            >
              <td className="px-3 py-2 font-mono text-xs">
                {thirdParty.formatted_document}
              </td>
              <td className="px-3 py-2">
                <span className={deleted ? "line-through opacity-60" : ""}>
                  {thirdParty.full_name}
                </span>
                {deleted && (
                  <span className="ml-2 rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] uppercase text-red-700 dark:text-red-400">
                    {t("deletedBadge")}
                  </span>
                )}
                {!thirdParty.is_active && !deleted && (
                  <span className="ml-2 rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] uppercase text-muted">
                    {t("inactiveBadge")}
                  </span>
                )}
              </td>
              <td className="hidden px-3 py-2 text-muted sm:table-cell">
                {t(`personTypes.${thirdParty.person_type}`)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
