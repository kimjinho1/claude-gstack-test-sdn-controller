import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api/client";

export interface Alarm {
  id: number;
  device_id: number;
  alarm_type: "DEVICE_DOWN" | "DEVICE_UP" | "INTERFACE_DOWN" | "INTERFACE_UP" | "POLL_TIMEOUT";
  severity: "CRITICAL" | "WARNING" | "INFO";
  message: string;
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  created_at: string;
  resolved_at: string | null;
}

export const useAlarmStore = defineStore("alarm", () => {
  const alarms = ref<Alarm[]>([]);
  const polling = ref<ReturnType<typeof setInterval> | null>(null);

  const openAlarms = computed(() => alarms.value.filter((a) => a.status === "OPEN"));
  const openCount = computed(() => openAlarms.value.length);

  async function fetchAlarms(status?: string) {
    const { data } = await api.get("/alarms", { params: status ? { status } : {} });
    alarms.value = data;
  }

  async function acknowledgeAlarm(id: number) {
    const { data } = await api.post(`/alarms/${id}/acknowledge`);
    const idx = alarms.value.findIndex((a) => a.id === id);
    if (idx !== -1) alarms.value[idx] = data;
  }

  async function addAction(alarmId: number, action_type: string, note?: string) {
    await api.post(`/alarms/${alarmId}/actions`, { action_type, note });
  }

  function startPolling(intervalMs = 3000) {
    if (polling.value) return;
    fetchAlarms("OPEN");
    polling.value = setInterval(() => fetchAlarms("OPEN"), intervalMs);
  }

  function stopPolling() {
    if (polling.value) {
      clearInterval(polling.value);
      polling.value = null;
    }
  }

  return {
    alarms, openAlarms, openCount,
    fetchAlarms, acknowledgeAlarm, addAction,
    startPolling, stopPolling,
  };
});
