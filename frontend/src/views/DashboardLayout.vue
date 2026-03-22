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
        <nav class="sidenav">
          <RouterLink to="/topology" class="nav-item" :class="{ active: route.path === '/topology' }">
            <span class="nav-icon">⬡</span> 토폴로지
          </RouterLink>
          <RouterLink to="/devices" class="nav-item" :class="{ active: route.path.startsWith('/devices') }">
            <span class="nav-icon">⊞</span> 장비 관리
          </RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/groups-manage" class="nav-item" :class="{ active: route.path === '/groups-manage' }">
            <span class="nav-icon">◫</span> 그룹 관리
          </RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/users" class="nav-item" :class="{ active: route.path === '/users' }">
            <span class="nav-icon">◉</span> 사용자 관리
          </RouterLink>
        </nav>

        <!-- Topology tree: only on devices section -->
        <TopologyTree v-if="route.path.startsWith('/devices')" @select="onTreeSelect" />
      </aside>

      <!-- Main Content -->
      <main class="content" :class="{ 'no-pad': route.path === '/topology' }">
        <RouterView :selected-building-id="selectedBuildingId" :selected-site-id="selectedSiteId" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { RouterView, RouterLink, useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useAlarmStore } from "@/stores/alarm";
import { useTopologyStore } from "@/stores/topology";
import TopologyTree from "@/components/TopologyTree.vue";

const auth = useAuthStore();
const alarmStore = useAlarmStore();
const topologyStore = useTopologyStore();
const router = useRouter();
const route = useRoute();

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
/* ── base ──────────────────────────────────────────────────────────────── */
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #0e1520;
  color: #d4dbe4;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── topbar ────────────────────────────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #111820;
  border-bottom: 1px solid #1a2a3a;
  padding: 0 1.25rem;
  height: 48px;
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
}
.logo {
  font-size: 1rem;
  font-weight: 800;
  color: #4dacf7;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.topbar-right { display: flex; align-items: center; gap: 0.9rem; }

.alarm-badge {
  padding: 0.25rem 0.65rem;
  border-radius: 20px;
  background: #162030;
  color: #6a8099;
  text-decoration: none;
  font-size: 0.8rem;
  border: 1px solid #1e2d3a;
  transition: all 0.15s;
}
.alarm-badge:hover { background: #1a2a3a; color: #d4dbe4; }
.alarm-badge.critical {
  background: #3a0a0a;
  color: #ff6b6b;
  border-color: #8b2222;
  animation: pulse-red 1.6s ease-in-out infinite;
}
@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 0 0 rgba(219,55,55,0.0); }
  50% { box-shadow: 0 0 0 4px rgba(219,55,55,0.3); }
}

.username { color: #6a8099; font-size: 0.83rem; }
.logout-btn {
  background: transparent;
  border: 1px solid #2a3a4a;
  color: #6a8099;
  padding: 0.25rem 0.65rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}
.logout-btn:hover { border-color: #6a8099; color: #d4dbe4; }

/* ── body ──────────────────────────────────────────────────────────────── */
.body { display: flex; flex: 1; min-height: 0; }

/* ── sidebar ───────────────────────────────────────────────────────────── */
.sidebar {
  width: 220px;
  background: #0e1520;
  border-right: 1px solid #1a2a3a;
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.sidenav {
  display: flex;
  flex-direction: column;
  padding: 0.6rem 0;
  border-bottom: 1px solid #1a2a3a;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.58rem 1rem;
  font-size: 0.85rem;
  color: #8fa0b4;
  text-decoration: none;
  transition: all 0.12s;
  border-left: 3px solid transparent;
}
.nav-item:hover { background: #131f2e; color: #d4dbe4; }
.nav-item.active {
  background: #0d1e30;
  color: #4dacf7;
  border-left-color: #1d6fa4;
  font-weight: 600;
}
.nav-icon {
  font-size: 0.9rem;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

/* ── content ───────────────────────────────────────────────────────────── */
.content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  background: #0e1520;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.content.no-pad {
  padding: 0;
  overflow: hidden;
}
</style>
