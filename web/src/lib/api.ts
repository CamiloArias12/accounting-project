import "server-only";

import { readToken } from "@/lib/session";
import type {
  Account,
  AccountCreate,
  AccountLevel,
  AccountNode,
  AccountUpdate,
  ImportResult,
} from "@/types/account";
import type {
  City,
  Country,
  Department,
  ThirdParty,
  ThirdPartyCreate,
  ThirdPartyListParams,
  ThirdPartyUpdate,
} from "@/types/third-party";
import type {
  AccountLedger,
  Company,
  Page,
  LedgerReport,
  Period,
  Voucher,
  VoucherCreate,
  VoucherListParams,
  VoucherReverse,
  VoucherUpdate,
} from "@/types/voucher";

// Resolved on the server, so it points at the service inside the Compose
// network. Not being NEXT_PUBLIC_* it never reaches the browser nor gets baked
// into the bundle: changing it does not require rebuilding the image.
const BASE_URL = process.env.API_URL ?? "http://api:8000";
const API = `${BASE_URL}/api/v1`;

/** An API failure carrying the backend's own message, not a generic one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    // The chart changes as it is edited; caching is governed by the server
    // actions' revalidation, not by the fetch cache.
    cache: "no-store",
    ...init,
    headers: await buildHeaders(init),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}

/**
 * FormData must not carry a Content-Type: the runtime sets it with the
 * multipart boundary, and overriding it makes the upload unparseable.
 */
async function buildHeaders(init?: RequestInit): Promise<HeadersInit> {
  const headers: Record<string, string> = init?.body instanceof FormData
    ? {}
    : { "Content-Type": "application/json" };

  const token = await readToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  return { ...headers, ...(init?.headers as Record<string, string> | undefined) };
}

/** FastAPI uses `detail`, which is either text or a list of validation errors. */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg ?? String(item)).join("; ");
    }
  } catch {
    // Empty or non-JSON body: fall through to the default message.
  }
  return `Error ${response.status}`;
}

export interface TreeOptions {
  rootCode?: string;
  /** Levels below the root; omit for the whole subtree. */
  maxDepth?: number;
  includeDeleted?: boolean;
}

export interface ListParams {
  level?: AccountLevel;
  parent_code?: string;
  search?: string;
  only_active?: boolean;
  /** Only accounts entries may be posted to: the leaves of the chart. */
  only_postable?: boolean;
  include_deleted?: boolean;
  skip?: number;
  limit?: number;
}

export interface Credentials {
  email: string;
  password: string;
}

export interface Session {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
}

export const authApi = {
  /** The OAuth2 password flow is form-encoded, not JSON. */
  login(credentials: Credentials): Promise<Session> {
    const body = new URLSearchParams({
      username: credentials.email,
      password: credentials.password,
    });
    return request<Session>("/auth/login", {
      method: "POST",
      body,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  me(): Promise<CurrentUser> {
    return request<CurrentUser>("/auth/me");
  },
};

export const accountsApi = {
  list(params: ListParams = {}): Promise<Page<Account>> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    const suffix = query.size > 0 ? `?${query}` : "";
    return request<Page<Account>>(`/accounts${suffix}`);
  },

  tree(options: TreeOptions = {}): Promise<AccountNode[]> {
    const query = new URLSearchParams();
    if (options.rootCode) query.set("root_code", options.rootCode);
    if (options.maxDepth !== undefined) {
      query.set("max_depth", String(options.maxDepth));
    }
    if (options.includeDeleted) query.set("include_deleted", "true");

    const suffix = query.size > 0 ? `?${query}` : "";
    return request<AccountNode[]>(`/accounts/tree${suffix}`);
  },

  get(code: string): Promise<Account> {
    return request<Account>(`/accounts/${code}`);
  },

  create(payload: AccountCreate): Promise<Account> {
    return request<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(code: string, payload: AccountUpdate): Promise<Account> {
    return request<Account>(`/accounts/${code}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  /** Soft delete: the account is kept and stamped with `deleted_at`. */
  remove(code: string): Promise<Account> {
    return request<Account>(`/accounts/${code}`, { method: "DELETE" });
  },

  restore(code: string): Promise<Account> {
    return request<Account>(`/accounts/${code}/restore`, { method: "POST" });
  },

  import(file: File, onExisting: "skip" | "update"): Promise<ImportResult> {
    const body = new FormData();
    body.append("file", file);
    return request<ImportResult>(`/accounts/import?on_existing=${onExisting}`, {
      method: "POST",
      body,
    });
  },
};

/** Turns a params object into a query string, dropping empty values. */
function toQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  return query.size > 0 ? `?${query}` : "";
}

export interface DepartmentParams {
  country_id?: number;
  search?: string;
  limit?: number;
}

export interface CityParams {
  department_id?: number;
  search?: string;
  limit?: number;
}

/** Read-only: the catalogs are seeded by migration, so there is nothing to write. */
export const locationsApi = {
  countries(search?: string): Promise<Country[]> {
    return request<Country[]>(`/locations/countries${toQuery({ search })}`);
  },

  departments(params: DepartmentParams = {}): Promise<Department[]> {
    return request<Department[]>(`/locations/departments${toQuery({ ...params })}`);
  },

  cities(params: CityParams = {}): Promise<City[]> {
    return request<City[]>(`/locations/cities${toQuery({ ...params })}`);
  },

  /** Resolves which department a stored city id belongs to. */
  city(id: number): Promise<City> {
    return request<City>(`/locations/cities/${id}`);
  },
};

export const thirdPartiesApi = {
  list(params: ThirdPartyListParams = {}): Promise<Page<ThirdParty>> {
    return request<Page<ThirdParty>>(`/third-parties${toQuery({ ...params })}`);
  },

  get(id: number, includeDeleted = false): Promise<ThirdParty> {
    const suffix = includeDeleted ? "?include_deleted=true" : "";
    return request<ThirdParty>(`/third-parties/${id}${suffix}`);
  },

  create(payload: ThirdPartyCreate): Promise<ThirdParty> {
    return request<ThirdParty>("/third-parties", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(id: number, payload: ThirdPartyUpdate): Promise<ThirdParty> {
    return request<ThirdParty>(`/third-parties/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  /** Soft delete: the row is kept and stamped with `deleted_at`. */
  remove(id: number): Promise<ThirdParty> {
    return request<ThirdParty>(`/third-parties/${id}`, { method: "DELETE" });
  },

  restore(id: number): Promise<ThirdParty> {
    return request<ThirdParty>(`/third-parties/${id}/restore`, {
      method: "POST",
    });
  },
};

export const vouchersApi = {
  /** The company the books belong to. Configuration, not a record. */
  company(): Promise<Company> {
    return request<Company>("/vouchers/company");
  },

  list(params: VoucherListParams = {}): Promise<Page<Voucher>> {
    return request<Page<Voucher>>(`/vouchers${toQuery({ ...params })}`);
  },

  get(id: number): Promise<Voucher> {
    return request<Voucher>(`/vouchers/${id}`);
  },

  create(payload: VoucherCreate): Promise<Voucher> {
    return request<Voucher>("/vouchers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(id: number, payload: VoucherUpdate): Promise<Voucher> {
    return request<Voucher>(`/vouchers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  /** Takes the next consecutive number and makes the voucher read-only. */
  post(id: number): Promise<Voucher> {
    return request<Voucher>(`/vouchers/${id}/post`, { method: "POST" });
  },

  /** Writes and posts the entry that cancels this one. */
  reverse(id: number, payload: VoucherReverse = {}): Promise<Voucher> {
    return request<Voucher>(`/vouchers/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /** Discards a draft. A posted voucher cannot be deleted. */
  remove(id: number): Promise<void> {
    return request<void>(`/vouchers/${id}`, { method: "DELETE" });
  },
};

export const periodsApi = {
  year(year: number): Promise<Period[]> {
    return request<Period[]>(`/periods/${year}`);
  },

  close(year: number, month: number): Promise<Period> {
    return request<Period>(`/periods/${year}/${month}/close`, {
      method: "POST",
    });
  },

  reopen(year: number, month: number): Promise<Period> {
    return request<Period>(`/periods/${year}/${month}/reopen`, {
      method: "POST",
    });
  },
};

export interface LedgerParams {
  date_from?: string;
  date_to?: string;
  account_code?: string;
  third_party_id?: number;
}

export const ledgerApi = {
  report(params: LedgerParams = {}): Promise<LedgerReport> {
    return request<LedgerReport>(`/ledger${toQuery({ ...params })}`);
  },

  account(code: string, params: LedgerParams = {}): Promise<AccountLedger> {
    return request<AccountLedger>(`/ledger/${code}${toQuery({ ...params })}`);
  },
};
