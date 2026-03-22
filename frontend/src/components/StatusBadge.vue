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
.managed { background: #c6f6d5; color: #22543d; }
.pending { background: #fefcbf; color: #744210; }
.error { background: #fed7d7; color: #742a2a; }
.unregistered { background: #e2e8f0; color: #4a5568; }
</style>
