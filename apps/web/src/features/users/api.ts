import { api } from "@/lib/api";
import type { User, UserRole } from "@/types";

export interface UsersListResponse {
  items: User[];
  total: number;
  page: number;
  pageSize: number;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  name: string;
  role: UserRole;
}

export interface UpdateUserPayload {
  role?: UserRole;
  is_active?: boolean;
}

export interface ListUsersParams {
  page?: number;
  size?: number;
  sort?: string;
  role?: string;
  is_active?: boolean;
}

export async function listUsersApi(params?: ListUsersParams): Promise<UsersListResponse> {
  const { data } = await api.get<UsersListResponse>("/users", { params });
  return data;
}

export async function createUserApi(payload: CreateUserPayload): Promise<User> {
  const { data } = await api.post<User>("/users", payload);
  return data;
}

export async function adminUpdateUserApi(
  userId: string,
  payload: UpdateUserPayload,
): Promise<User> {
  const { data } = await api.patch<User>(`/users/${userId}`, payload);
  return data;
}

export async function updateOnboardingStepApi(step: number): Promise<User> {
  const { data } = await api.patch<User>("/users/me/onboarding-step", { step });
  return data;
}
