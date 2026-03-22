import { describe, it, expect } from "vitest";

// Extracted from SwitchPortMap.vue
const SHORT_MAP: [RegExp, string][] = [
  [/^GigabitEthernet/, "Gi"],
  [/^TenGigabitEthernet/, "Te"],
  [/^FastEthernet/, "Fa"],
  [/^HundredGigabitEthernet/, "Hu"],
  [/^FortyGigabitEthernet/, "Fo"],
  [/^Ethernet/, "Et"],
  [/^Management/, "Ma"],
  [/^Loopback/, "Lo"],
  [/^Vlan/, "Vl"],
];

function shortName(name: string): string {
  for (const [re, abbr] of SHORT_MAP) {
    if (re.test(name)) return name.replace(re, abbr);
  }
  return name.length > 6 ? name.slice(0, 6) : name;
}

describe("shortName", () => {
  it("abbreviates GigabitEthernet", () => {
    expect(shortName("GigabitEthernet0/1")).toBe("Gi0/1");
  });

  it("abbreviates TenGigabitEthernet", () => {
    expect(shortName("TenGigabitEthernet1/0/1")).toBe("Te1/0/1");
  });

  it("abbreviates FastEthernet", () => {
    expect(shortName("FastEthernet0/0")).toBe("Fa0/0");
  });

  it("abbreviates Ethernet", () => {
    expect(shortName("Ethernet1")).toBe("Et1");
  });

  it("abbreviates Management", () => {
    expect(shortName("Management0")).toBe("Ma0");
  });

  it("abbreviates Loopback", () => {
    expect(shortName("Loopback0")).toBe("Lo0");
  });

  it("abbreviates Vlan", () => {
    expect(shortName("Vlan10")).toBe("Vl10");
  });

  it("truncates unknown long names to 6 chars", () => {
    expect(shortName("PortChannel1")).toBe("PortCh");
  });

  it("returns short unknown names as-is", () => {
    expect(shortName("eth0")).toBe("eth0");
  });
});
