"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  /** Secondary line under the label — a code, a document number. */
  hint?: string;
}

interface Props {
  /**
   * Field name. When given, a real `<select>` carries the value so the form
   * still posts and still validates; omit it for filters that only drive the
   * URL and have no form behind them.
   */
  name?: string;
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  /**
   * Number of options from which the search box appears. Below it, searching
   * is friction: four options are read faster than they are typed.
   */
  searchFrom?: number;
}

/** Beyond this the list is cut and the search box is the way through. */
const MAX_VISIBLE = 100;

/**
 * A select you can type into.
 *
 * The problem it solves is that half the lists in this app are catalogs, not
 * choices: 1,122 municipalities and 250 countries in a native dropdown are
 * navigable only by scrolling. The problem it must not create is a control
 * that posts nothing — every form here is a Server Action reading `FormData`.
 *
 * So the visible control is a listbox and the value lives in a real `<select>`
 * parked behind it: `FormData` picks it up, `required` is enforced by the
 * browser, and the form still works with JavaScript off. The select is
 * transparent rather than hidden because a `display:none` control is exempt
 * from validation, and the browser refuses to report an error it cannot point
 * at — the submit would fail silently instead.
 */
export function SearchableSelect({
  name,
  value,
  defaultValue,
  onChange,
  options,
  placeholder,
  searchPlaceholder,
  emptyLabel,
  disabled = false,
  required = false,
  className,
  searchFrom = 6,
}: Props) {
  const t = useTranslations("select");

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [uncontrolled, setUncontrolled] = useState(defaultValue ?? "");
  const searchRef = useRef<HTMLInputElement>(null);

  const current = value ?? uncontrolled;
  const selected = options.find((option) => option.value === current);
  const searchable = options.length >= searchFrom;

  const matches = useMemo(() => {
    const needle = normalize(query);
    if (!needle) return options;

    // Every word has to appear somewhere, in any order: "bogota cundi" finds
    // the row whichever way round the user remembers it.
    const words = needle.split(/\s+/);
    return options.filter((option) => {
      const haystack = normalize(
        `${option.label} ${option.hint ?? ""} ${option.value}`,
      );
      return words.every((word) => haystack.includes(word));
    });
  }, [options, query]);

  const visible = matches.slice(0, MAX_VISIBLE);
  const hidden = matches.length - visible.length;

  function choose(next: string) {
    if (value === undefined) setUncontrolled(next);
    onChange?.(next);
    setOpen(false);
  }

  return (
    <div className={cn("relative", className)}>
      {name && (
        <select
          name={name}
          value={current}
          required={required}
          disabled={disabled}
          onChange={(event) => choose(event.target.value)}
          aria-hidden
          tabIndex={-1}
          className="pointer-events-none absolute bottom-0 left-3 size-px opacity-0"
        >
          <option value="" />
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}

      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          // Cleared on close rather than on open, so the list is never seen
          // filtered by last time's query for a frame.
          if (!next) setQuery("");
        }}
      >
        <PopoverTrigger
          render={
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={open}
              disabled={disabled || options.length === 0}
              className={cn(
                "w-full justify-between gap-2 font-normal",
                !selected && "text-muted-foreground",
              )}
            >
              <span className="truncate">
                {selected?.label ?? placeholder ?? t("placeholder")}
              </span>
              <ChevronsUpDown className="shrink-0 opacity-50" />
            </Button>
          }
        />
        <PopoverContent
          className="w-(--anchor-width) min-w-56 p-0"
          align="start"
          // Without this Base UI focuses the popup itself and the first
          // keystroke goes nowhere — the search box has to be live on open.
          initialFocus={searchable ? searchRef : undefined}
        >
          {/* `shouldFilter={false}`: the matching above is accent-insensitive,
              which cmdk's own is not — "Boyaca" has to find "Boyacá". */}
          <Command shouldFilter={false}>
            {searchable && (
              <CommandInput
                ref={searchRef}
                placeholder={searchPlaceholder ?? t("search")}
                value={query}
                onValueChange={setQuery}
              />
            )}
            <CommandList className="scrollbar-slim">
              <CommandEmpty>{emptyLabel ?? t("empty")}</CommandEmpty>
              <CommandGroup>
                {visible.map((option) => (
                  <CommandItem
                    key={option.value}
                    value={option.value}
                    onSelect={() => choose(option.value)}
                  >
                    <Check
                      className={cn(
                        "text-primary",
                        option.value === current ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate">{option.label}</span>
                      {option.hint && (
                        <span className="truncate text-xs text-muted-foreground">
                          {option.hint}
                        </span>
                      )}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
              {hidden > 0 && (
                <p className="border-t border-border/60 px-3 py-2 text-xs text-muted-foreground">
                  {t("more", { count: hidden })}
                </p>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

/** Lowercased and stripped of accents, so "Medellin" matches "Medellín". */
function normalize(value: string): string {
  return value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}
