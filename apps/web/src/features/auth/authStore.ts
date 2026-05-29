import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";
import { clearAccessToken, setAccessToken } from "@/lib/api";
import { logoutApi } from "@/features/auth/api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (user: User, accessToken: string) => void;
  setUser: (user: User) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setAuth: (user, accessToken) => {
        setAccessToken(accessToken);
        set({ user, isAuthenticated: true });
      },

      setUser: (user) => {
        set({ user });
      },

      logout: async () => {
        try {
          await logoutApi();
        } catch {
          // best-effort: denylist may already be gone
        }
        clearAccessToken();
        set({ user: null, isAuthenticated: false });
        window.location.href = "/login";
      },
    }),
    {
      name: "retailflux-auth",
      // Only persist non-sensitive fields (NOT the token — that stays in memory)
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
