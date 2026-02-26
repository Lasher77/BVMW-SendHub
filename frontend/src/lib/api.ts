import type {
  Campaign,
  CampaignListItem,
  CampaignAsset,
  CampaignComment,
  CampaignFile,
  Department,
  AppSettings,
  User,
  CampaignStatus,
  LoginResponse,
  SetupStatus,
} from "@/types";

const BASE = "/api";

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

export function setToken(token: string) {
  localStorage.setItem("auth_token", token);
}

export function clearToken() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setStoredUser(user: User) {
  localStorage.setItem("auth_user", JSON.stringify(user));
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// ---------------------------------------------------------------------------
// Base request helper
// ---------------------------------------------------------------------------
function getDevUser(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("x-user") || "";
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };

  // Auth: prefer JWT token, fall back to X-User for dev mode
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    const devUser = getDevUser();
    if (devUser) {
      headers["X-User"] = devUser;
    }
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail?.message || json?.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Public request — no auth headers attached. */
async function publicRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail?.message || json?.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------- Auth ----------
export const login = async (
  email: string,
  password: string
): Promise<LoginResponse> => {
  const resp = await publicRequest<LoginResponse>("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  setToken(resp.access_token);
  setStoredUser(resp.user);
  return resp;
};

export const logout = () => {
  clearToken();
};

export const getSetupStatus = () =>
  publicRequest<SetupStatus>("/setup-status");

export const setup = async (
  name: string,
  email: string,
  password: string
): Promise<LoginResponse> => {
  const resp = await publicRequest<LoginResponse>("/setup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
  setToken(resp.access_token);
  setStoredUser(resp.user);
  return resp;
};

export const getMe = () => request<User>("/me");

// ---------- Users (admin) ----------
export const getUsers = () => request<User[]>("/users");

export const createUser = (data: {
  name: string;
  email: string;
  password: string;
}) =>
  request<User>("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const updateUser = (
  id: number,
  data: { name?: string; password?: string; is_active?: boolean }
) =>
  request<User>(`/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const deleteUser = (id: number) =>
  request<void>(`/users/${id}`, { method: "DELETE" });

// ---------- Departments ----------
export const getDepartments = () => publicRequest<Department[]>("/departments");
export const createDepartment = (data: { name: string; is_active: boolean }) =>
  request<Department>("/departments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
export const updateDepartment = (
  id: number,
  data: Partial<{ name: string; is_active: boolean }>
) =>
  request<Department>(`/departments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

// ---------- Settings ----------
export const getSettings = () => request<AppSettings>("/settings");
export const updateSettings = (data: { min_gap_days: number }) =>
  request<AppSettings>("/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

// ---------- Campaigns ----------
export const getCampaigns = (params?: { status?: string; department_id?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.department_id) q.set("department_id", String(params.department_id));
  const qs = q.toString() ? `?${q.toString()}` : "";
  return request<CampaignListItem[]>(`/campaigns${qs}`);
};

export const getCampaign = (id: number) =>
  request<Campaign>(`/campaigns/${id}`);

/** Campaign creation is public (no auth). Requester email/name are in the FormData. */
export const createCampaign = (formData: FormData) =>
  publicRequest<Campaign>("/campaigns", { method: "POST", body: formData });

export const updateCampaignStatus = (
  id: number,
  data: { status?: CampaignStatus; send_at?: string | null; reason?: string | null }
) =>
  request<Campaign>(`/campaigns/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const uploadPdf = (id: number, file: File) => {
  const fd = new FormData();
  fd.append("pdf", file);
  return request<CampaignFile>(`/campaigns/${id}/files`, { method: "POST", body: fd });
};

export const uploadAsset = (id: number, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return request<CampaignAsset>(`/campaigns/${id}/assets`, { method: "POST", body: fd });
};

export const getAssets = (id: number) =>
  request<CampaignAsset[]>(`/campaigns/${id}/assets`);

export const deleteAsset = (campaignId: number, assetId: number) =>
  request<void>(`/campaigns/${campaignId}/assets/${assetId}`, { method: "DELETE" });

export const addComment = (id: number, text: string) =>
  request<CampaignComment>(`/campaigns/${id}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

// ---------- Schedule ----------
export const getNextAvailable = (channel = "email") =>
  publicRequest<{ next_available: string }>(`/schedule/next-available?channel=${channel}`);

export const getMoveOptions = (id: number, start: string, end: string) =>
  request<{ valid_dates: string[] }>(`/campaigns/${id}/move-options?start=${start}&end=${end}`);
