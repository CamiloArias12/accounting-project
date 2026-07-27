// Types and constants for the account server actions.
import type { ImportResult } from "@/types/account";

export type FormState =
  | { status: "idle" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

export type ImportState =
  | { status: "idle" }
  | { status: "success"; result: ImportResult }
  | { status: "error"; message: string };

export const IDLE: FormState = { status: "idle" };
export const IMPORT_IDLE: ImportState = { status: "idle" };
