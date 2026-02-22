export type UserRole = "requester" | "marketing";

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  department_id: number | null;
}

export interface Department {
  id: number;
  name: string;
  is_active: boolean;
}

export interface AppSettings {
  id: number;
  min_gap_days: number;
}

export type CampaignStatus =
  | "submitted"
  | "in_review"
  | "changes_needed"
  | "scheduled"
  | "approved"
  | "rejected"
  | "sent";

export interface CampaignFile {
  id: number;
  version: number;
  original_filename: string;
  file_size: number;
  uploaded_at: string;
  uploaded_by: User;
}

export interface CampaignAsset {
  id: number;
  original_filename: string;
  sanitized_filename: string;
  mime_type: string;
  file_size: number;
  is_deleted: boolean;
  uploaded_at: string;
  uploaded_by: User;
}

export interface CampaignComment {
  id: number;
  text: string;
  created_at: string;
  author: User;
}

export interface CampaignMoveLog {
  id: number;
  old_send_at: string | null;
  new_send_at: string | null;
  reason: string | null;
  created_at: string;
  moved_by: User;
}

export interface Campaign {
  id: number;
  title: string;
  channel: string;
  status: CampaignStatus;
  send_at: string | null;
  created_at: string;
  updated_at: string;
  department: Department;
  creator: User;
  files: CampaignFile[];
  assets: CampaignAsset[];
  comments: CampaignComment[];
  move_logs: CampaignMoveLog[];
}

export interface CampaignListItem {
  id: number;
  title: string;
  channel: string;
  status: CampaignStatus;
  send_at: string | null;
  created_at: string;
  department: Department;
  creator: User;
}
