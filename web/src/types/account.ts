/**
 * The Spanish values are the contract with the API and the source spreadsheet,
 * which ship them verbatim. Only the labels shown to the user are translated.
 */
export const NATURES = ["Debito", "Crédito"] as const;
export type Nature = (typeof NATURES)[number];

export const LEVELS = [
  "Clase",
  "Grupo",
  "Cuenta",
  "Subcuenta",
  "Auxiliar",
] as const;
export type AccountLevel = (typeof LEVELS)[number];

export const NATURE_LABELS: Record<Nature, string> = {
  Debito: "Debit",
  Crédito: "Credit",
};

export const LEVEL_LABELS: Record<AccountLevel, string> = {
  Clase: "Class",
  Grupo: "Group",
  Cuenta: "Account",
  Subcuenta: "Subaccount",
  Auxiliar: "Auxiliary",
};

export interface Account {
  code: string;
  name: string;
  nature: Nature;
  level: AccountLevel;
  parent_code: string | null;
  is_active: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountNode extends Account {
  children: AccountNode[];
}

export interface AccountCreate {
  code: string;
  name: string;
  nature: Nature;
  is_active?: boolean;
}

export interface AccountUpdate {
  name?: string;
  nature?: Nature;
  is_active?: boolean;
}

export interface RowError {
  row: number;
  code: string | null;
  message: string;
}

export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: RowError[];
}
