import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/api/client";

export interface Building {
  id: number;
  site_id: number;
  name: string;
  floors: number;
  device_count: number;
}

export interface Site {
  id: number;
  group_id: number;
  name: string;
  description: string | null;
  buildings: Building[];
}

export interface Group {
  id: number;
  name: string;
  description: string | null;
  sites: Site[];
}

export const useTopologyStore = defineStore("topology", () => {
  const groups = ref<Group[]>([]);
  const loading = ref(false);

  async function fetchGroups() {
    loading.value = true;
    try {
      const { data } = await api.get("/groups");
      groups.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function createGroup(name: string, description?: string) {
    const { data } = await api.post("/groups", { name, description });
    groups.value.push({ ...data, sites: [] });
    return data;
  }

  async function createSite(group_id: number, name: string, description?: string) {
    const { data } = await api.post("/sites", { group_id, name, description });
    const group = groups.value.find((g) => g.id === group_id);
    if (group) group.sites.push({ ...data, buildings: [] });
    return data;
  }

  async function createBuilding(site_id: number, name: string, floors: number) {
    const { data } = await api.post("/buildings", { site_id, name, floors });
    for (const g of groups.value) {
      const site = g.sites.find((s) => s.id === site_id);
      if (site) {
        site.buildings.push({ ...data, device_count: 0 });
        break;
      }
    }
    return data;
  }

  async function deleteGroup(id: number) {
    await api.delete(`/groups/${id}`);
    groups.value = groups.value.filter((g) => g.id !== id);
  }

  async function deleteSite(id: number) {
    await api.delete(`/sites/${id}`);
    for (const g of groups.value) {
      g.sites = g.sites.filter((s) => s.id !== id);
    }
  }

  async function deleteBuilding(id: number) {
    await api.delete(`/buildings/${id}`);
    for (const g of groups.value) {
      for (const s of g.sites) {
        s.buildings = s.buildings.filter((b) => b.id !== id);
      }
    }
  }

  return {
    groups, loading,
    fetchGroups, createGroup, createSite, createBuilding,
    deleteGroup, deleteSite, deleteBuilding,
  };
});
