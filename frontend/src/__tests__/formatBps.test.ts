import { describe, it, expect } from "vitest";

// Extracted from SwitchPortMap.vue — pure utility, no Vue dependency needed
function formatBps(bps: number | null | undefined): string {
  if (bps === null || bps === undefined) return "—";
  if (bps < 1000) return `${Math.round(bps)} bps`;
  if (bps < 1_000_000) return `${(bps / 1000).toFixed(1)} Kbps`;
  return `${(bps / 1_000_000).toFixed(1)} Mbps`;
}

describe("formatBps", () => {
  it("returns — for null", () => {
    expect(formatBps(null)).toBe("—");
  });

  it("returns — for undefined", () => {
    expect(formatBps(undefined)).toBe("—");
  });

  it("formats sub-1000 as bps", () => {
    expect(formatBps(0)).toBe("0 bps");
    expect(formatBps(500)).toBe("500 bps");
    expect(formatBps(999)).toBe("999 bps");
  });

  it("formats 1000–999999 as Kbps", () => {
    expect(formatBps(1000)).toBe("1.0 Kbps");
    expect(formatBps(500_000)).toBe("500.0 Kbps");
  });

  it("formats 1000000+ as Mbps", () => {
    expect(formatBps(1_000_000)).toBe("1.0 Mbps");
    expect(formatBps(100_000_000)).toBe("100.0 Mbps");
  });
});
