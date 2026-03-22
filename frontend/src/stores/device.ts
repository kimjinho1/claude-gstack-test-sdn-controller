import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/api/client";

export interface Device {
  id: number;
  name: string;
  mac_addr: string;
  ip_addr: string;
  site_id: number;
  building_id: number;
  floor: number | null;
  protocol: "SSH" | "REST";
  status: "UNREGISTERED" | "PENDING" | "MANAGED" | "ERROR";
  uptime: string | null;
  serial_no: string | null;
  model: string | null;
  sw_version: string | null;
  last_polled_at: string | null;
  created_at: string;
}

export const useDeviceStore = defineStore("device", () => {
  const devices = ref<Device[]>([]);
  const loading = ref(false);

  async function fetchDevices(params?: { site_id?: number; building_id?: number; status?: string }) {
    loading.value = true;
    try {
      const { data } = await api.get("/devices", { params });
      devices.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function createDevice(payload: Record<string, unknown>) {
    const { data } = await api.post("/devices", payload);
    devices.value.push(data);
    return data;
  }

  async function deleteDevice(id: number) {
    await api.delete(`/devices/${id}`);
    devices.value = devices.value.filter((d) => d.id !== id);
  }

  async function getPorts(deviceId: number) {
    const { data } = await api.get(`/devices/${deviceId}/ports`);
    return data;
  }

  async function getVlans(deviceId: number) {
    const { data } = await api.get(`/devices/${deviceId}/vlans`);
    return data;
  }

  async function getEndpoints(deviceId: number) {
    const { data } = await api.get(`/devices/${deviceId}/endpoints`);
    return data;
  }

  return {
    devices, loading,
    fetchDevices, createDevice, deleteDevice,
    getPorts, getVlans, getEndpoints,
  };
});
