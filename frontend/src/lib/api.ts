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
} from "@/types";

const BASE = "/api";

function getUser(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("x-user") || "requester@bvmw.example";
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "X-User": getUser(),
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
export const getMe = () => request<User>("/me");

// ---------- Departments ----------
export const getDepartments = () => request<Department[]>("/departments");
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

export const createCampaign = (formData: FormData) =>
  request<Campaign>("/campaigns", { method: "POST", body: formData });

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
  request<{ next_available: string }>(`/schedule/next-available?channel=${channel}`);

export const getMoveOptions = (id: number, start: string, end: string) =>
  request<{ valid_dates: string[] }>(`/campaigns/${id}/move-options?start=${start}&end=${end}`);
