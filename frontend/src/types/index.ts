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

  // Profile import / CV fields
  headline: string | null;
  summary: string | null;
  skills: SkillItem[];
  education: EducationItem[];
  work_experience: ExperienceItem[];
  linkedin_url: string | null;
  infojobs_url: string | null;
  cv_file_url: string | null;
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

  // Profile import / CV fields
  headline?: string | null;
  summary?: string | null;
  skills?: SkillItem[];
  education?: EducationItem[];
  work_experience?: ExperienceItem[];
  linkedin_url?: string | null;
  infojobs_url?: string | null;
  cv_file_url?: string | null;
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
  job_url: string | null;
  portal_name: string;
  cover_letter_generated: boolean;
  cover_letter_text: string | null;
  error_message: string | null;
  submitted_at: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Profile import / CV types
// ---------------------------------------------------------------------------

export interface SkillItem {
  name: string;
  level: string; // beginner | intermediate | advanced | expert
}

export interface EducationItem {
  institution: string;
  degree: string;
  field: string | null;
  start_date: string;
  end_date: string | null;
  description: string | null;
}

export interface ExperienceItem {
  company: string;
  role: string;
  start_date: string;
  end_date: string | null;
  description: string | null;
  current: boolean;
}

export interface ImportedProfile {
  headline: string | null;
  summary: string | null;
  skills: SkillItem[];
  education: EducationItem[];
  work_experience: ExperienceItem[];
  linkedin_url: string | null;
  infojobs_url: string | null;
}

export interface CVParseResult {
  id: string;
  file_name: string;
  file_size: number;
  parsed_data: ImportedProfile;
}

export interface NotificationPreferences {
  in_app: boolean;
  email: boolean;
  on_submit: boolean;
  on_fail: boolean;
  on_match: boolean;
}

export interface MergeRequest {
  preview_data: ImportedProfile;
  strategy?: string;
}
