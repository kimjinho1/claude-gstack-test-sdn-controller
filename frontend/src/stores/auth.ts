import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api/client";

export interface User {
  id: number;
  username: string;
  role: "SUPERADMIN" | "ADMIN" | "VIEWER";
  is_active: boolean;
  must_change_password: boolean;
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const token = ref<string | null>(localStorage.getItem("access_token"));

  const isLoggedIn = computed(() => !!token.value);
  const isSuperAdmin = computed(() => user.value?.role === "SUPERADMIN");
  const isAdmin = computed(() => ["SUPERADMIN", "ADMIN"].includes(user.value?.role ?? ""));

  async function login(username: string, password: string) {
    const { data } = await api.post("/auth/login", { username, password });
    token.value = data.access_token;
    localStorage.setItem("access_token", data.access_token);
    await fetchMe();
  }

  async function fetchMe() {
    const { data } = await api.get("/auth/me");
    user.value = data;
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    if (user.value) user.value.must_change_password = false;
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem("access_token");
  }

  return { user, token, isLoggedIn, isSuperAdmin, isAdmin, login, fetchMe, changePassword, logout };
});
