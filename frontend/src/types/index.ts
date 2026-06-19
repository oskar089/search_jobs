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
