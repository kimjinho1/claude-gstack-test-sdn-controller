<template>
  <div class="layout" :class="{ 'sidebar-collapsed': !sidebarOpen }">
    <!-- Top Bar -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" @click="sidebarOpen = !sidebarOpen" title="사이드바 토글">
          <span class="hamburger">☰</span>
        </button>
        <span class="logo">SDN Controller</span>
      </div>
      <div class="topbar-right">
        <RouterLink to="/alarms" class="alarm-badge" :class="{ critical: alarmStore.openCount > 0 }">
          🔔 알람 {{ alarmStore.openCount }}
        </RouterLink>
        <button class="icon-btn tree-toggle-btn" @click="treeOpen = !treeOpen" title="그룹 트리">
          🌲
        </button>
        <button class="icon-btn theme-btn" @click="themeStore.toggleTheme()" :title="themeStore.isDark ? '라이트 모드' : '다크 모드'">
          {{ themeStore.isDark ? '☀️' : '🌙' }}
        </button>
        <span class="username">{{ auth.user?.username }}</span>
        <button class="logout-btn" @click="logout">로그아웃</button>
      </div>
    </header>

    <div class="body">
      <!-- Sidebar -->
      <Transition name="sidebar">
        <aside v-show="sidebarOpen" class="sidebar">
          <nav class="sidenav">
            <RouterLink to="/topology" class="nav-item" :class="{ active: route.path === '/topology' }">
              <span class="nav-icon">⬡</span> <span class="nav-label">토폴로지</span>
            </RouterLink>
            <RouterLink to="/devices" class="nav-item" :class="{ active: route.path.startsWith('/devices') }">
              <span class="nav-icon">⊞</span> <span class="nav-label">장비 관리</span>
            </RouterLink>
            <RouterLink to="/alarms" class="nav-item" :class="{ active: route.path === '/alarms' }">
              <span class="nav-icon">🔔</span> <span class="nav-label">알람</span>
            </RouterLink>
            <RouterLink v-if="auth.isAdmin" to="/groups-manage" class="nav-item" :class="{ active: route.path === '/groups-manage' }">
              <span class="nav-icon">◫</span> <span class="nav-label">그룹 관리</span>
            </RouterLink>
            <RouterLink v-if="auth.isAdmin" to="/users" class="nav-item" :class="{ active: route.path === '/users' }">
              <span class="nav-icon">◉</span> <span class="nav-label">사용자 관리</span>
            </RouterLink>
          </nav>
        </aside>
      </Transition>

      <!-- Group Tree Panel (overlay, all routes) -->
      <Transition name="tree-panel">
        <div v-if="treeOpen" class="tree-panel">
          <div class="tree-panel-header">
            <span>그룹 트리</span>
            <button class="close-btn" @click="treeOpen = false">✕</button>
          </div>
          <TopologyTree @select="onTreeSelect" />
        </div>
      </Transition>

      <!-- Main Content -->
      <main class="content" :class="{ 'no-pad': route.path === '/topology' }">
        <RouterView :selected-building-id="selectedBuildingId" :selected-site-id="selectedSiteId" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterView, RouterLink, useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlarmStore } from '@/stores/alarm'
import { useTopologyStore } from '@/stores/topology'
import { useThemeStore } from '@/stores/theme'
import TopologyTree from '@/components/TopologyTree.vue'

const auth = useAuthStore()
const alarmStore = useAlarmStore()
const topologyStore = useTopologyStore()
const themeStore = useThemeStore()
const router = useRouter()
const route = useRoute()

const sidebarOpen = ref(true)
const treeOpen = ref(false)
const selectedSiteId = ref<number | undefined>()
const selectedBuildingId = ref<number | undefined>()

function onTreeSelect(payload: { siteId?: number; buildingId?: number }) {
  selectedSiteId.value = payload.siteId
  selectedBuildingId.value = payload.buildingId
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  topologyStore.fetchGroups()
  alarmStore.startPolling(3000)
})

onUnmounted(() => {
  alarmStore.stopPolling()
})
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── topbar ─────────────────────────────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-topbar);
  border-bottom: 1px solid var(--border-color);
  padding: 0 1rem;
  height: 48px;
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
}
.topbar-left { display: flex; align-items: center; gap: 0.6rem; }
.logo {
  font-size: 1rem;
  font-weight: 800;
  color: var(--accent-hover);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.topbar-right { display: flex; align-items: center; gap: 0.75rem; }

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: var(--text-secondary);
  padding: 0.25rem 0.4rem;
  border-radius: 4px;
  line-height: 1;
  transition: all 0.12s;
}
.icon-btn:hover { background: var(--bg-elevated); color: var(--text-primary); }

.alarm-badge {
  padding: 0.25rem 0.65rem;
  border-radius: 20px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.8rem;
  border: 1px solid var(--border-subtle);
  transition: all 0.15s;
}
.alarm-badge:hover { background: var(--bg-surface); color: var(--text-primary); }
.alarm-badge.critical {
  background: var(--danger-bg);
  color: #ff6b6b;
  border-color: var(--danger);
  animation: pulse-red 1.6s ease-in-out infinite;
}
@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 0 0 rgba(219,55,55,0.0); }
  50% { box-shadow: 0 0 0 4px rgba(219,55,55,0.3); }
}

.username { color: var(--text-muted); font-size: 0.83rem; }
.logout-btn {
  background: transparent;
  border: 1px solid var(--border-input);
  color: var(--text-secondary);
  padding: 0.25rem 0.65rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}
.logout-btn:hover { border-color: var(--text-secondary); color: var(--text-primary); }

/* ── body ───────────────────────────────────────────────────────────────── */
.body { display: flex; flex: 1; min-height: 0; position: relative; }

/* ── sidebar ────────────────────────────────────────────────────────────── */
.sidebar {
  width: 180px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.sidenav {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 0.9rem;
  font-size: 0.84rem;
  color: var(--nav-text);
  text-decoration: none;
  transition: all 0.12s;
  border-left: 3px solid transparent;
  white-space: nowrap;
  overflow: hidden;
}
.nav-item:hover { background: var(--nav-hover-bg); color: var(--text-primary); }
.nav-item.active {
  background: var(--nav-active-bg);
  color: var(--nav-active-text);
  border-left-color: var(--nav-active-border);
  font-weight: 600;
}
.nav-icon {
  font-size: 0.88rem;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}
.nav-label { overflow: hidden; text-overflow: ellipsis; }

/* Sidebar slide transition */
.sidebar-enter-active, .sidebar-leave-active { transition: width 0.2s ease; overflow: hidden; }
.sidebar-enter-from, .sidebar-leave-to { width: 0; }

/* ── group tree panel ───────────────────────────────────────────────────── */
.tree-panel {
  width: 220px;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}
.tree-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  flex-shrink: 0;
}
.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.9rem;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  transition: all 0.12s;
}
.close-btn:hover { background: var(--bg-surface); color: var(--text-primary); }

/* Tree panel slide transition */
.tree-panel-enter-active, .tree-panel-leave-active { transition: width 0.2s ease; overflow: hidden; }
.tree-panel-enter-from, .tree-panel-leave-to { width: 0; }

/* ── content ────────────────────────────────────────────────────────────── */
.content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  background: var(--bg-base);
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.content.no-pad {
  padding: 0;
  overflow: hidden;
}
</style>
