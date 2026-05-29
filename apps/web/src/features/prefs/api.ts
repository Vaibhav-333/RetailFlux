import { api } from "@/lib/api";

interface PrefsPatch {
  density?: "comfortable" | "compact";
  theme?: "dark" | "light";
}

export async function updateUserPrefsApi(patch: PrefsPatch): Promise<void> {
  await api.patch("/users/me/prefs", patch);
}
