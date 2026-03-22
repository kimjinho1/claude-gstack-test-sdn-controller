<template>
  <div class="layout">
    <!-- Top Bar -->
    <header class="topbar">
      <div class="topbar-left">
        <span class="logo">SDN Controller</span>
      </div>
      <div class="topbar-right">
        <RouterLink to="/alarms" class="alarm-badge" :class="{ critical: alarmStore.openCount > 0 }">
          🔔 알람 {{ alarmStore.openCount }}
        </RouterLink>
        <span class="username">{{ auth.user?.username }}</span>
        <button class="logout-btn" @click="logout">로그아웃</button>
      </div>
    </header>

    <div class="body">
      <!-- Sidebar -->
      <aside class="sidebar">
        <TopologyTree @select="onTreeSelect" />
      </aside>

      <!-- Main Content -->
      <main class="content">
        <RouterView :selected-building-id="selectedBuildingId" :selected-site-id="selectedSiteId" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { RouterView, RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useAlarmStore } from "@/stores/alarm";
import { useTopologyStore } from "@/stores/topology";
import TopologyTree from "@/components/TopologyTree.vue";

const auth = useAuthStore();
const alarmStore = useAlarmStore();
const topologyStore = useTopologyStore();
const router = useRouter();

const selectedSiteId = ref<number | undefined>();
const selectedBuildingId = ref<number | undefined>();

function onTreeSelect(payload: { siteId?: number; buildingId?: number }) {
  selectedSiteId.value = payload.siteId;
  selectedBuildingId.value = payload.buildingId;
}

function logout() {
  auth.logout();
  router.push("/login");
}

onMounted(() => {
  topologyStore.fetchGroups();
  alarmStore.startPolling(3000);
});

onUnmounted(() => {
  alarmStore.stopPolling();
});
</script>

<style scoped>
.layout { display: flex; flex-direction: column; min-height: 100vh; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: #1a202c; color: white; padding: 0 1.5rem; height: 52px;
  position: sticky; top: 0; z-index: 100;
}
.logo { font-size: 1.1rem; font-weight: 700; color: #63b3ed; }
.topbar-right { display: flex; align-items: center; gap: 1rem; }
.alarm-badge {
  padding: 0.3rem 0.7rem; border-radius: 20px;
  background: #2d3748; color: #a0aec0; text-decoration: none; font-size: 0.85rem;
  transition: background 0.2s;
}
.alarm-badge.critical { background: #c53030; color: white; }
.username { color: #a0aec0; font-size: 0.9rem; }
.logout-btn {
  background: none; border: 1px solid #4a5568; color: #a0aec0;
  padding: 0.3rem 0.7rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem;
}
.logout-btn:hover { border-color: #a0aec0; color: white; }
.body { display: flex; flex: 1; }
.sidebar { width: 260px; background: white; border-right: 1px solid #e2e8f0; overflow-y: auto; flex-shrink: 0; }
.content { flex: 1; padding: 1.5rem; overflow-y: auto; }
</style>
