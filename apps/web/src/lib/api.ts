import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,   // sends httpOnly refresh-token cookie
});

// Attach access token from memory on every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Silent refresh on 401
let refreshing: Promise<string> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        if (!refreshing) {
          refreshing = refreshAccessToken().finally(() => { refreshing = null; });
        }
        const newToken = await refreshing;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch {
        clearAccessToken();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ─── In-memory token store ────────────────────────────────────────────────────
let _accessToken: string | null = null;

export function setAccessToken(token: string) { _accessToken = token; }
export function getAccessToken() { return _accessToken; }
export function clearAccessToken() { _accessToken = null; }

export async function refreshAccessToken(): Promise<string> {
  const { data } = await axios.post<{ access_token: string }>(
    `${BASE_URL}/api/v1/auth/refresh`,
    {},
    { withCredentials: true }
  );
  setAccessToken(data.access_token);
  return data.access_token;
}
