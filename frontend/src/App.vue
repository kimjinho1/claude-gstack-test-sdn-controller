<template>
  <RouterView />
</template>

<script setup lang="ts">
import '@/styles/theme.css'
import { RouterView } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
useThemeStore()
</script>

<style>
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg-base);
  color: var(--text-primary);
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--scrollbar-track); }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 3px; }
</style>
