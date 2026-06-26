import { api } from "./api";
import type { TokenResponse, UserResponse, LoginRequest, RegisterRequest } from "../types";

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function registerUser(data: RegisterRequest): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function refreshToken(): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/refresh", {
    method: "POST",
  });
}

export async function getMe(): Promise<UserResponse> {
  return api<UserResponse>("/auth/me");
}

export async function logoutUser(): Promise<void> {
  await api<{ message: string }>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
