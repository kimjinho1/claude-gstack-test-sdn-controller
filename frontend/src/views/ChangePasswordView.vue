<template>
  <div class="login-page">
    <div class="login-card">
      <h1>비밀번호 변경</h1>
      <p class="subtitle">보안을 위해 최초 로그인 시 비밀번호를 변경해주세요.</p>

      <form @submit.prevent="handleChange">
        <div class="field">
          <label>현재 비밀번호</label>
          <input v-model="current" type="password" required />
        </div>
        <div class="field">
          <label>새 비밀번호 (6자 이상)</label>
          <input v-model="newPw" type="password" required minlength="6" />
        </div>
        <div class="field">
          <label>새 비밀번호 확인</label>
          <input v-model="confirm" type="password" required />
        </div>

        <div v-if="error" class="error">{{ error }}</div>
        <div v-if="success" class="success">{{ success }}</div>

        <button type="submit" :disabled="loading">
          {{ loading ? "변경 중..." : "변경하기" }}
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

const current = ref("");
const newPw = ref("");
const confirm = ref("");
const error = ref("");
const success = ref("");
const loading = ref(false);

async function handleChange() {
  error.value = "";
  if (newPw.value !== confirm.value) {
    error.value = "새 비밀번호가 일치하지 않습니다.";
    return;
  }
  loading.value = true;
  try {
    await auth.changePassword(current.value, newPw.value);
    success.value = "비밀번호가 변경되었습니다.";
    setTimeout(() => router.push("/devices"), 1500);
  } catch (e: any) {
    error.value = e.response?.data?.detail || "변경에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-base); }
.login-card {
  background: var(--bg-surface); border: 1px solid var(--border-color);
  border-radius: 12px; padding: 2.5rem; width: 380px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
h1 { font-size: 1.4rem; font-weight: 700; color: var(--accent-hover); }
.subtitle { color: var(--text-muted); margin-top: 0.25rem; margin-bottom: 2rem; font-size: 0.85rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; font-size: 0.85rem; font-weight: 500; margin-bottom: 0.4rem; color: var(--text-secondary); }
.field input {
  width: 100%; padding: 0.6rem 0.8rem;
  border: 1px solid var(--border-input); border-radius: 6px; font-size: 0.95rem; outline: none;
  background: var(--bg-input); color: var(--text-primary);
}
.field input:focus { border-color: var(--accent-primary); }
.error { color: var(--danger); font-size: 0.85rem; margin-bottom: 1rem; }
.success { color: var(--success); font-size: 0.85rem; margin-bottom: 1rem; }
button {
  width: 100%; padding: 0.7rem; background: var(--accent-primary); color: white;
  border: none; border-radius: 6px; font-size: 1rem; font-weight: 500;
  cursor: pointer; transition: opacity 0.2s;
}
button:hover:not(:disabled) { opacity: 0.9; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
