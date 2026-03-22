<template>
  <div class="login-page">
    <div class="login-card">
      <h1>SDN Controller</h1>
      <p class="subtitle">네트워크 관리 플랫폼</p>

      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>아이디</label>
          <input v-model="username" type="text" placeholder="username" autocomplete="username" required />
        </div>
        <div class="field">
          <label>비밀번호</label>
          <input v-model="password" type="password" placeholder="password" autocomplete="current-password" required />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" :disabled="loading">
          {{ loading ? "로그인 중..." : "로그인" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function handleLogin() {
  error.value = "";
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    if (auth.user?.must_change_password) {
      router.push("/change-password");
    } else {
      router.push("/devices");
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || "로그인에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
}
.login-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 2.5rem;
  width: 360px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
h1 { font-size: 1.5rem; font-weight: 700; color: var(--accent-hover); }
.subtitle { color: var(--text-muted); margin-top: 0.25rem; margin-bottom: 2rem; font-size: 0.9rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; font-size: 0.85rem; font-weight: 500; margin-bottom: 0.4rem; color: var(--text-secondary); }
.field input {
  width: 100%; padding: 0.6rem 0.8rem;
  border: 1px solid var(--border-input); border-radius: 6px;
  font-size: 0.95rem; outline: none; transition: border-color 0.2s;
  background: var(--bg-input); color: var(--text-primary);
}
.field input:focus { border-color: var(--accent-primary); }
.error { color: var(--danger); font-size: 0.85rem; margin-bottom: 1rem; }
button {
  width: 100%; padding: 0.7rem;
  background: var(--accent-primary); color: white; border: none;
  border-radius: 6px; font-size: 1rem; font-weight: 500;
  cursor: pointer; transition: opacity 0.2s;
}
button:hover:not(:disabled) { opacity: 0.9; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
