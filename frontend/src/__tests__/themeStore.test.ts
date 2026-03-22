import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useThemeStore } from "@/stores/theme";

describe("useThemeStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("defaults to dark theme when localStorage has no entry", () => {
    const store = useThemeStore();
    expect(store.isDark).toBe(true);
  });

  it("reads 'light' from localStorage on init", () => {
    localStorage.setItem("theme", "light");
    const store = useThemeStore();
    expect(store.isDark).toBe(false);
  });

  it("toggleTheme flips isDark", () => {
    const store = useThemeStore();
    expect(store.isDark).toBe(true);
    store.toggleTheme();
    expect(store.isDark).toBe(false);
    store.toggleTheme();
    expect(store.isDark).toBe(true);
  });

  it("toggleTheme persists to localStorage", () => {
    const store = useThemeStore();
    store.toggleTheme(); // → light
    expect(localStorage.getItem("theme")).toBe("light");
    store.toggleTheme(); // → dark
    expect(localStorage.getItem("theme")).toBe("dark");
  });
});
