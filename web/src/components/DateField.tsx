"use client";

import { CalendarIcon } from "lucide-react";
import { useLocale } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Props {
  name: string;
  /** ISO `yyyy-mm-dd`, which is what the API speaks. */
  defaultValue?: string;
  placeholder: string;
  required?: boolean;
  readOnly?: boolean;
}

/**
 * A date field that reads in the user's language.
 *
 * The native `<input type="date">` renders in the *browser's* locale, so a
 * Spanish app on an English machine shows `mm/dd/yyyy` — which for 03/04 is
 * not a formatting quibble but a different day.
 *
 * The value still travels as ISO in a hidden input: what the user reads and
 * what the server parses are deliberately not the same string.
 */
export function DateField({
  name,
  defaultValue = "",
  placeholder,
  required = false,
  readOnly = false,
}: Props) {
  const locale = useLocale();
  const [value, setValue] = useState(defaultValue);
  const [open, setOpen] = useState(false);

  const selected = value ? parseIso(value) : undefined;

  return (
    <>
      <input type="hidden" name={name} value={value} required={required} />
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              variant="outline"
              type="button"
              disabled={readOnly}
              className={cn(
                "w-full justify-start font-normal",
                !value && "text-muted-foreground",
              )}
            >
              <CalendarIcon />
              {selected ? format(selected, locale) : placeholder}
            </Button>
          }
        />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selected}
            defaultMonth={selected}
            onSelect={(day) => {
              if (day) setValue(toIso(day));
              setOpen(false);
            }}
          />
        </PopoverContent>
      </Popover>
    </>
  );
}

/**
 * Parsed as local time, not UTC.
 *
 * `new Date("2026-07-26")` is midnight UTC, which west of Greenwich is the
 * 25th — the calendar would highlight the wrong day.
 */
function parseIso(value: string): Date | undefined {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return undefined;
  return new Date(year, month - 1, day);
}

function toIso(date: Date): string {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function format(date: Date, locale: string): string {
  return date.toLocaleDateString(locale, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}
