<template>
  <Teleport to="body">
    <Transition name="drawer-bg">
      <div v-if="modelValue" class="drawer-backdrop" />
    </Transition>
    <Transition name="drawer-slide">
      <div v-if="modelValue" class="drawer" :style="{ width: drawerWidth + 'px' }">
        <!-- Resize handle on left edge -->
        <div class="resize-handle" @mousedown="startResize" />

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
import { ref, watch } from "vue";

const props = defineProps<{ modelValue: boolean; title: string; width?: number }>();
defineEmits<{ (e: "update:modelValue", v: boolean): void }>();

const MIN_WIDTH = 380;
const MAX_WIDTH = 1200;
const drawerWidth = ref(props.width ?? 480);

watch(() => props.width, (v) => { if (v) drawerWidth.value = v; });

let startX = 0;
let startWidth = 0;

function startResize(e: MouseEvent) {
  e.preventDefault();
  startX = e.clientX;
  startWidth = drawerWidth.value;
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", stopResize);
  document.body.style.cursor = "ew-resize";
  document.body.style.userSelect = "none";
}

function onMouseMove(e: MouseEvent) {
  const delta = startX - e.clientX; // drag left → delta positive → increase width
  const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + delta));
  drawerWidth.value = newWidth;
}

function stopResize() {
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", stopResize);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
}
</script>

<style scoped>
.drawer-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 400;
}
.drawer {
  position: fixed; top: 0; right: 0; height: 100vh;
  background: var(--bg-modal); z-index: 401;
  display: flex; flex-direction: column;
  box-shadow: -6px 0 40px rgba(0,0,0,0.4);
  border-left: 1px solid var(--border-subtle);
}

/* Resize handle — 8px grab zone on the left edge */
.resize-handle {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 8px;
  cursor: ew-resize;
  z-index: 10;
}
.resize-handle::after {
  content: '';
  position: absolute;
  left: 2px; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 40px;
  border-radius: 2px;
  background: var(--border-subtle);
  opacity: 0;
  transition: opacity 0.15s;
}
.resize-handle:hover::after { opacity: 1; }

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
