"use client";

import { Check, ChevronsUpDown, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

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

export interface Option {
  value: string;
  label: string;
  hint?: string;
}

interface Props {
  value: string;
  /** Shown on the trigger before anything has been searched. */
  selectedLabel?: string;
  placeholder: string;
  searchPlaceholder: string;
  emptyLabel: string;
  search: (query: string) => Promise<Option[]>;
  onChange: (option: Option | null) => void;
  disabled?: boolean;
}

/**
 * A picker that looks things up on the server as you type.
 *
 * Not a `<select>`: the chart of accounts has 2,449 rows and the third party
 * master grows without limit, so the list has to be narrowed before it reaches
 * the browser. Where the list is finite and already in hand, SearchableSelect
 * is the one to reach for — it posts its own value and needs no round trip.
 *
 * Built on Command, which brings what the hand-rolled version was missing:
 * arrow keys, Enter to choose, Escape to close, focus returned to the trigger,
 * and a listbox a screen reader can actually walk.
 */
export function AsyncCombobox({
  value,
  selectedLabel,
  placeholder,
  searchPlaceholder,
  emptyLabel,
  search,
  onChange,
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [loading, setLoading] = useState(false);

  // Debounced, so typing a six-digit code is one lookup and not six.
  useEffect(() => {
    if (!open) return;

    // The flag is raised inside the timer, not in the effect body: setting
    // state synchronously there costs an extra render on every keystroke.
    const timer = setTimeout(() => {
      setLoading(true);
      search(query)
        .then(setOptions)
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, open, search]);

  const chosen = options.find((option) => option.value === value);
  const label = chosen?.label ?? selectedLabel ?? "";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-between gap-2 font-normal",
              !label && "text-muted-foreground",
            )}
          >
            <span className="truncate">{label || placeholder}</span>
            <ChevronsUpDown className="shrink-0 opacity-50" />
          </Button>
        }
      />
      <PopoverContent className="w-(--anchor-width) min-w-72 p-0" align="start">
        {/* `shouldFilter={false}`: the filtering already happened on the
            server, and letting cmdk filter again would hide rows the query
            legitimately matched by code. */}
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList className="scrollbar-slim">
            <CommandEmpty>
              {loading ? (
                <span className="flex items-center justify-center gap-2 text-muted-foreground">
                  <LoaderCircle className="size-4 animate-spin" />
                </span>
              ) : (
                emptyLabel
              )}
            </CommandEmpty>
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.value}
                  onSelect={() => {
                    onChange(option.value === value ? null : option);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "text-primary",
                      option.value === value ? "opacity-100" : "opacity-0",
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
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
