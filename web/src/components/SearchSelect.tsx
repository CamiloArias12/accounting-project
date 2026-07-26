"use client";

import { useEffect, useId, useRef, useState } from "react";

export interface Option {
  value: string;
  label: string;
  hint?: string;
}

interface Props {
  value: string;
  /** Shown when a value is already chosen but the list has not been searched. */
  selectedLabel?: string;
  placeholder: string;
  search: (query: string) => Promise<Option[]>;
  onChange: (option: Option | null) => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

/**
 * A text box that looks things up as you type.
 *
 * Not a `<select>`: the chart of accounts has 2,449 rows and the third party
 * master grows without limit, so the list has to be narrowed on the server
 * before it reaches the browser at all.
 */
export function SearchSelect({
  value,
  selectedLabel,
  placeholder,
  search,
  onChange,
  required = false,
  disabled = false,
  className = "",
}: Props) {
  const [query, setQuery] = useState(selectedLabel ?? "");
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  // A combobox has to name the list it controls, or a screen reader has no way
  // to reach the options it just announced.
  const listId = useId();

  // Debounced, so typing a six-digit code is one lookup and not six.
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(() => {
      search(query).then(setOptions);
    }, 250);
    return () => clearTimeout(timer);
  }, [query, open, search]);

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, []);

  function choose(option: Option) {
    setQuery(option.label);
    setOpen(false);
    onChange(option);
  }

  return (
    <div ref={box} className={`relative ${className}`}>
      <input
        value={query}
        placeholder={placeholder}
        disabled={disabled}
        required={required && !value}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          // Clearing the box clears the choice: leaving the old id behind
          // while the text says something else is how wrong entries happen.
          if (!event.target.value) onChange(null);
        }}
        className="w-full rounded-md border border-border bg-transparent px-2 py-1.5 text-sm disabled:opacity-50"
      />

      {/* A real listbox, not just a styled list: without the roles it is
          indistinguishable from any other list on the page, to a screen reader
          as much as to anything else. */}
      {open && options.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-60 w-full min-w-64 overflow-y-auto rounded-md border border-border bg-card shadow-lg"
        >
          {options.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value}
                onClick={() => choose(option)}
                className="flex w-full flex-col items-start gap-0.5 px-3 py-1.5 text-left text-sm hover:bg-foreground/5"
              >
                <span>{option.label}</span>
                {option.hint && (
                  <span className="text-xs text-muted-foreground">{option.hint}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
