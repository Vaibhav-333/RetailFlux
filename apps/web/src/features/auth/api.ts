import { api } from "@/lib/api";
import type { User } from "@/types";

export interface RegisterPayload {
  company_name: string;
  email: string;
  password: string;
  name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export async function registerApi(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/register", payload);
  return data;
}

export async function loginApi(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/login", payload);
  return data;
}

export async function logoutApi(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getMeApi(): Promise<User> {
  const { data } = await api.get<User>("/users/me");
  return data;
}

export async function updateUserApi(payload: { name?: string }): Promise<User> {
  const { data } = await api.patch<User>("/users/me", payload);
  return data;
}
