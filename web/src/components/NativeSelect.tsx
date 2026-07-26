"use client";

import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface Props {
  name: string;
  defaultValue?: string;
  value?: string;
  onChange?: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

/**
 * A styled native `<select>`.
 *
 * shadcn's Select is a button plus a listbox, which looks better but posts
 * nothing: these forms are Server Actions reading `FormData`, so a control that
 * submits its own value is not a compromise, it is the requirement. Progressive
 * enhancement comes free with it — the forms still work with no JavaScript.
 */
export function NativeSelect({
  name,
  defaultValue,
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  required = false,
  className,
}: Props) {
  return (
    <div className={cn("relative", className)}>
      <select
        name={name}
        defaultValue={defaultValue}
        value={value}
        required={required}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.value)}
        className="h-8 w-full appearance-none rounded-lg border border-border bg-transparent py-1 pl-2.5 pr-8 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-4 -translate-y-1/2 opacity-50" />
    </div>
  );
}
