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
  list(params: ListParams = {}): Promise<Account[]> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    const suffix = query.size > 0 ? `?${query}` : "";
    return request<Account[]>(`/accounts${suffix}`);
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
  list(params: ThirdPartyListParams = {}): Promise<ThirdParty[]> {
    return request<ThirdParty[]>(`/third-parties${toQuery({ ...params })}`);
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
