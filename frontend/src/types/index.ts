export interface UserResponse {
  id: string;
  email: string;
  name: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Profile {
  id: string;
  user_id: string;
  target_roles: string[];
  tech_stack: string[];
  experience_level: string;
  min_salary: number | null;
  max_salary: number | null;
  locations: string[];
  remote_only: boolean;
  languages: string[];
  is_active: boolean;
}

export interface ProfileUpdate {
  target_roles?: string[];
  tech_stack?: string[];
  experience_level?: string;
  min_salary?: number | null;
  max_salary?: number | null;
  locations?: string[];
  remote_only?: boolean;
  languages?: string[];
  is_active?: boolean;
}

export interface PortalSelectors {
  job_card: string;
  title: string;
  company: string;
  location?: string | null;
  description: string;
  url: string;
  salary?: string | null;
  posted_date?: string | null;
  apply_button?: string | null;
}

export interface Portal {
  id: string;
  name: string;
  base_url: string;
  job_listing_url: string;
  selectors: PortalSelectors;
  is_builtin: boolean;
  is_enabled: boolean;
  is_verified: boolean;
  scrape_interval_min: number;
  created_at: string;
  updated_at: string;
}

export interface PortalCreate {
  name: string;
  base_url: string;
  job_listing_url: string;
  selectors: PortalSelectors;
  scrape_interval_min?: number;
}

export interface Notification {
  id: string;
  user_id: string;
  application_id: string | null;
  type: string;
  channel: string;
  title: string;
  body: string;
  is_read: boolean;
  sent_at: string;
  read_at: string | null;
}

export interface Application {
  id: string;
  stored_job_id: string;
  pipeline_run_id: string | null;
  status: string;
  match_score: number | null;
  company: string;
  job_title: string;
  portal_name: string;
  cover_letter_generated: boolean;
  submitted_at: string | null;
  created_at: string;
}
