import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "Login", component: () => import("@/views/LoginView.vue"), meta: { public: true } },
    { path: "/change-password", name: "ChangePassword", component: () => import("@/views/ChangePasswordView.vue") },
    {
      path: "/",
      component: () => import("@/views/DashboardLayout.vue"),
      children: [
        { path: "", redirect: "/devices" },
        { path: "devices", name: "Devices", component: () => import("@/views/DevicesView.vue") },
        { path: "devices/:id", name: "DeviceDetail", component: () => import("@/views/DeviceDetailView.vue") },
        { path: "alarms", name: "Alarms", component: () => import("@/views/AlarmsView.vue") },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/devices" },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore();

  if (to.meta.public) return next();

  if (!auth.isLoggedIn) return next("/login");

  if (!auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      return next("/login");
    }
  }

  // Force password change
  if (auth.user?.must_change_password && to.name !== "ChangePassword") {
    return next("/change-password");
  }

  next();
});

export default router;
