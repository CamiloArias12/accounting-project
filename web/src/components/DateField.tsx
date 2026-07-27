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
  // ISO `yyyy-mm-dd`, which is what the API speaks.
  defaultValue?: string;
  placeholder: string;
  required?: boolean;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}

export function DateField({
  name,
  defaultValue = "",
  placeholder,
  required = false,
  readOnly = false,
  onChange,
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
              if (day) {
                const iso = toIso(day);
                setValue(iso);
                onChange?.(iso);
              }
              setOpen(false);
            }}
          />
        </PopoverContent>
      </Popover>
    </>
  );
}

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
