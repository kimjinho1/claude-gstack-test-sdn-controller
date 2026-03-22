<template>
  <span class="badge" :class="status.toLowerCase()">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ status: string }>();

const label = computed(() => {
  const map: Record<string, string> = {
    MANAGED: "🟢 MANAGED",
    PENDING: "🟡 PENDING",
    ERROR: "🔴 ERROR",
    UNREGISTERED: "⚪ 미등록",
  };
  return map[props.status] ?? props.status;
});
</script>

<style scoped>
.badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 500; white-space: nowrap; }
.managed { background: rgba(0,168,84,0.15); color: var(--success); }
.pending { background: rgba(217,130,43,0.15); color: var(--warning); }
.error { background: rgba(194,48,48,0.15); color: var(--danger); }
.unregistered { background: var(--bg-elevated); color: var(--text-muted); }
</style>
