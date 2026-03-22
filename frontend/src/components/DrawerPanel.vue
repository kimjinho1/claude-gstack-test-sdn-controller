<template>
  <Teleport to="body">
    <Transition name="drawer-bg">
      <div v-if="modelValue" class="drawer-backdrop" @click.self="$emit('update:modelValue', false)" />
    </Transition>
    <Transition name="drawer-slide">
      <div v-if="modelValue" class="drawer" :style="{ width: width + 'px' }">
        <div class="drawer-header">
          <h3>{{ title }}</h3>
          <button class="close-btn" @click="$emit('update:modelValue', false)">✕</button>
        </div>
        <div class="drawer-body">
          <slot />
        </div>
        <div v-if="$slots.footer" class="drawer-footer">
          <slot name="footer" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean; title: string; width?: number }>();
defineEmits<{ (e: "update:modelValue", v: boolean): void }>();
</script>

<style scoped>
.drawer-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 400;
}
.drawer {
  position: fixed; top: 0; right: 0; height: 100vh; width: 480px;
  background: var(--bg-modal); z-index: 401;
  display: flex; flex-direction: column;
  box-shadow: -6px 0 40px rgba(0,0,0,0.4);
  border-left: 1px solid var(--border-subtle);
}
.drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem; border-bottom: 1px solid var(--border-subtle); flex-shrink: 0;
}
.drawer-header h3 {
  font-size: 0.88rem; font-weight: 700; margin: 0; color: var(--text-primary);
  text-transform: uppercase; letter-spacing: 0.06em;
}
.close-btn {
  background: none; border: none; cursor: pointer; font-size: 1rem;
  color: var(--text-muted); padding: 0.2rem 0.5rem; border-radius: 3px; line-height: 1; transition: all 0.12s;
}
.close-btn:hover { background: var(--bg-elevated); color: var(--text-primary); }
.drawer-body { flex: 1; overflow-y: auto; padding: 1.25rem; }
.drawer-footer {
  padding: 0.85rem 1.25rem; border-top: 1px solid var(--border-subtle);
  display: flex; gap: 0.5rem; justify-content: flex-end; flex-shrink: 0;
  background: var(--bg-elevated);
}

/* Transitions */
.drawer-bg-enter-active, .drawer-bg-leave-active { transition: opacity 0.2s; }
.drawer-bg-enter-from, .drawer-bg-leave-to { opacity: 0; }
.drawer-slide-enter-active, .drawer-slide-leave-active { transition: transform 0.25s ease; }
.drawer-slide-enter-from, .drawer-slide-leave-to { transform: translateX(100%); }
</style>
