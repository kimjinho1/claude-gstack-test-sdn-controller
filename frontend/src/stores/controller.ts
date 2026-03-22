import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/api/client";

export interface DeviceModel {
  id: number;
  name: string;
  vendor: string;
  device_type: string;
  description: string | null;
  image_url: string | null;
  docker_image: string | null;
  is_virtual: boolean;
  created_at: string;
}

export interface VirtualDevice {
  id: number;
  name: string;
  model_id: number;
  container_id: string | null;
  ssh_port: number;
  status: "starting" | "running" | "stopped" | "error";
  created_at: string;
  stopped_at: string | null;
}

export const useControllerStore = defineStore("controller", () => {
  const deviceModels = ref<DeviceModel[]>([]);
  const virtualDevices = ref<VirtualDevice[]>([]);

  // ── Device Models ──────────────────────────────────────────────────────────

  async function fetchDeviceModels() {
    const { data } = await api.get("/controller/device-models");
    deviceModels.value = data;
  }

  async function createDeviceModel(payload: Partial<DeviceModel>) {
    const { data } = await api.post("/controller/device-models", payload);
    deviceModels.value.push(data);
    return data as DeviceModel;
  }

  async function updateDeviceModel(id: number, payload: Partial<DeviceModel>) {
    const { data } = await api.patch(`/controller/device-models/${id}`, payload);
    const idx = deviceModels.value.findIndex((m) => m.id === id);
    if (idx !== -1) deviceModels.value[idx] = data;
    return data as DeviceModel;
  }

  async function deleteDeviceModel(id: number) {
    await api.delete(`/controller/device-models/${id}`);
    deviceModels.value = deviceModels.value.filter((m) => m.id !== id);
  }

  // ── Virtual Devices ────────────────────────────────────────────────────────

  async function fetchVirtualDevices() {
    const { data } = await api.get("/controller/virtual-devices");
    virtualDevices.value = data;
  }

  async function launchVirtualDevice(payload: { name: string; model_id: number; ssh_port: number }) {
    const { data } = await api.post("/controller/virtual-devices", payload);
    virtualDevices.value.push(data);
    return data as VirtualDevice;
  }

  async function stopVirtualDevice(id: number) {
    const { data } = await api.post(`/controller/virtual-devices/${id}/stop`);
    const idx = virtualDevices.value.findIndex((v) => v.id === id);
    if (idx !== -1) virtualDevices.value[idx] = data;
  }

  async function deleteVirtualDevice(id: number) {
    await api.delete(`/controller/virtual-devices/${id}`);
    virtualDevices.value = virtualDevices.value.filter((v) => v.id !== id);
  }

  return {
    deviceModels, virtualDevices,
    fetchDeviceModels, createDeviceModel, updateDeviceModel, deleteDeviceModel,
    fetchVirtualDevices, launchVirtualDevice, stopVirtualDevice, deleteVirtualDevice,
  };
});
