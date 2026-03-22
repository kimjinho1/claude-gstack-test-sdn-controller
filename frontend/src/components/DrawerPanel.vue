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
  position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 400;
}
.drawer {
  position: fixed; top: 0; right: 0; height: 100vh; width: 440px;
  background: white; z-index: 401;
  display: flex; flex-direction: column;
  box-shadow: -4px 0 32px rgba(0,0,0,0.14);
}
.drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.drawer-header h3 { font-size: 1rem; font-weight: 700; margin: 0; color: #1a202c; }
.close-btn {
  background: none; border: none; cursor: pointer; font-size: 1.1rem;
  color: #a0aec0; padding: 0.2rem 0.4rem; border-radius: 4px; line-height: 1;
}
.close-btn:hover { background: #f7fafc; color: #4a5568; }
.drawer-body { flex: 1; overflow-y: auto; padding: 1.5rem; }
.drawer-footer {
  padding: 1rem 1.5rem; border-top: 1px solid #e2e8f0;
  display: flex; gap: 0.5rem; justify-content: flex-end; flex-shrink: 0;
}

/* Transitions */
.drawer-bg-enter-active, .drawer-bg-leave-active { transition: opacity 0.2s; }
.drawer-bg-enter-from, .drawer-bg-leave-to { opacity: 0; }
.drawer-slide-enter-active, .drawer-slide-leave-active { transition: transform 0.25s ease; }
.drawer-slide-enter-from, .drawer-slide-leave-to { transform: translateX(100%); }
</style>
