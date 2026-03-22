import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/api/client";
import type { UserRole } from "./auth";

export interface ManagedUser {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  must_change_password: boolean;
}

export const useUserManageStore = defineStore("userManage", () => {
  const users = ref<ManagedUser[]>([]);
  const loading = ref(false);

  async function fetchUsers() {
    loading.value = true;
    try {
      const { data } = await api.get("/users");
      users.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function createUser(payload: { username: string; password: string; role: UserRole; must_change_password?: boolean }) {
    const { data } = await api.post("/users", payload);
    users.value.push(data);
    return data as ManagedUser;
  }

  async function updateUser(id: number, payload: Partial<{ username: string; password: string; role: UserRole; is_active: boolean; must_change_password: boolean }>) {
    const { data } = await api.patch(`/users/${id}`, payload);
    const idx = users.value.findIndex((u) => u.id === id);
    if (idx !== -1) users.value[idx] = data;
  }

  async function deleteUser(id: number) {
    await api.delete(`/users/${id}`);
    users.value = users.value.filter((u) => u.id !== id);
  }

  async function bulkDelete(ids: number[]) {
    await api.post("/users/bulk-delete", { ids });
    users.value = users.value.filter((u) => !ids.includes(u.id));
  }

  return { users, loading, fetchUsers, createUser, updateUser, deleteUser, bulkDelete };
});
