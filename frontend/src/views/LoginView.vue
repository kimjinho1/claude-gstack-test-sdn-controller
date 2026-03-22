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
  background: #1a202c;
}
.login-card {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  width: 360px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}
h1 { font-size: 1.5rem; font-weight: 700; color: #1a202c; }
.subtitle { color: #718096; margin-top: 0.25rem; margin-bottom: 2rem; font-size: 0.9rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; font-size: 0.85rem; font-weight: 500; margin-bottom: 0.4rem; color: #4a5568; }
.field input {
  width: 100%; padding: 0.6rem 0.8rem;
  border: 1px solid #e2e8f0; border-radius: 6px;
  font-size: 0.95rem; outline: none; transition: border-color 0.2s;
}
.field input:focus { border-color: #4299e1; }
.error { color: #e53e3e; font-size: 0.85rem; margin-bottom: 1rem; }
button {
  width: 100%; padding: 0.7rem;
  background: #4299e1; color: white; border: none;
  border-radius: 6px; font-size: 1rem; font-weight: 500;
  cursor: pointer; transition: background 0.2s;
}
button:hover:not(:disabled) { background: #3182ce; }
button:disabled { background: #a0aec0; cursor: not-allowed; }
</style>
