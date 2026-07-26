/**
 * Types and constants for the account server actions.
 *
 * They live outside `actions.ts` on purpose: a `"use server"` module may only
 * export async functions, so exporting a plain object from there makes Next
 * fail the whole route with "A 'use server' file can only export async
 * functions, found object".
 */
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
