"""
Mock Arista cEOS SSH Server
- Accepts any SSH username/password
- Responds to Arista EOS CLI commands used by Netmiko/NAPALM polling
"""
import os
import socket
import threading
import time

import paramiko

# Generate host key at startup (ephemeral — regenerated each container start)
HOST_KEY = paramiko.RSAKey.generate(2048)

HOSTNAME = os.environ.get("MOCK_HOSTNAME", "arista-gw-01")

SHOW_VERSION = f"""\
Arista DCS-7280CR3-32P4-F
Hardware version:    11.00
Serial number:       JPE99887766
System MAC address:  aabb.cc00.0001

Software image version: 4.32.0F
Architecture:           x86_64
Internal build version: 4.32.0F-mock
cEOS tools version:     1.1
Kernel version:         5.15.0-generic

Uptime:                 0 weeks, 0 days, 0 hours and 2 minutes
Total memory:           8192016 kB
Free memory:            6744528 kB
"""

SHOW_IP_INT_BRIEF = """\
Interface              IP Address         Status     Protocol            MTU
Ethernet1              10.0.0.1/24        up         up                 1500
Ethernet2              unassigned         up         up                 1500
Management0            172.20.0.2/24      up         up                 1500
"""

SHOW_INTERFACES = """\
Ethernet1 is up, line protocol is up (connected)
  Hardware is Ethernet, address is aabb.cc00.0001 (bia aabb.cc00.0001)
  Description: Uplink to Core
  Internet address is 10.0.0.1/24
  Broadcast address is 255.255.255.255
  IP MTU 1500 bytes, BW 1000000 kbit
  Full-duplex, 1Gb/s, auto negotiation: on, uni-link: n/a
  Up 0 hours, 2 minutes, 10 seconds
  0 input errors, 0 input discards
  10000 packets input, 1234567890 bytes
  10000 packets output, 987654321 bytes
Ethernet2 is up, line protocol is up (connected)
  Hardware is Ethernet, address is aabb.cc00.0002 (bia aabb.cc00.0002)
  Description: Access port VLAN20
  Internet address is unassigned
  IP MTU 1500 bytes, BW 1000000 kbit
  Full-duplex, 1Gb/s, auto negotiation: on
  Up 0 hours, 2 minutes, 10 seconds
  5000 packets input, 456789012 bytes
  5000 packets output, 123456789 bytes
Management0 is up, line protocol is up (connected)
  Hardware is Ethernet, address is aabb.cc00.00ff (bia aabb.cc00.00ff)
  Internet address is 172.20.0.2/24
  IP MTU 1500 bytes
  Full-duplex, 1Gb/s, auto negotiation: on
  1000 packets input, 98765432 bytes
  1000 packets output, 12345678 bytes
"""

SHOW_INTERFACES_SWITCHPORT = """\
Name: Ethernet1
  Switchport: Enabled
  Administrative Mode: access
  Operational Mode: access
  Access Mode VLAN: 10 (MGMT)
  Trunking Native Mode VLAN: 1 (default)
  Administrative Native VLAN tagging: disabled
  Trunking VLANs Enabled: NONE

Name: Ethernet2
  Switchport: Enabled
  Administrative Mode: trunk
  Operational Mode: trunk
  Access Mode VLAN: 1 (default)
  Trunking Native Mode VLAN: 1 (default)
  Administrative Native VLAN tagging: disabled
  Trunking VLANs Enabled: 10,20

Name: Management0
  Switchport: Not Enabled
  Administrative Mode: routed
  Operational Mode: routed
"""

SHOW_VLAN = """\
VLAN  Name                             Status    Ports
----- -------------------------------- --------- -------------------------------
1     default                          active
10    MGMT                             active    Et1
20    DATA                             active    Et2
"""

SHOW_MAC_TABLE = """\
          Mac Address Table
------------------------------------------------------------------

Vlan    Mac Address       Type        Ports      Moves   Last Move
----    -----------       ----        -----      -----   ---------
  10    aabb.cc00.0002    DYNAMIC     Et1        1       0:00:05 ago
  20    aabb.cc00.0003    DYNAMIC     Et2        1       0:00:10 ago
Total Mac Addresses for this criterion: 2
"""


class EosServerInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return "password,publickey"

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_exec_request(self, channel, command):
        return True


def _prompt(enabled: bool) -> str:
    return f"\r\n{HOSTNAME}#" if enabled else f"\r\n{HOSTNAME}>"


def handle_client(client_socket):
    transport = paramiko.Transport(client_socket)
    transport.add_server_key(HOST_KEY)
    server = EosServerInterface()
    try:
        transport.start_server(server=server)
    except Exception as e:
        print(f"[mock-ceos] Transport start failed: {e}", flush=True)
        return

    channel = transport.accept(20)
    if channel is None:
        transport.close()
        return

    # Wait for shell to be ready
    time.sleep(0.3)

    enabled = False
    channel.sendall(f"\r\nArista Networks EOS version 4.32.0F running on {HOSTNAME}")
    channel.sendall(f"\r\n{HOSTNAME}>")

    buf = ""
    try:
        while transport.is_active():
            if channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="ignore")
                for char in data:
                    if char in ("\r", "\n"):
                        cmd = buf.strip()
                        buf = ""

                        if not cmd:
                            channel.sendall(_prompt(enabled))
                            continue

                        # Echo command back (Netmiko expects to see the command echoed)
                        channel.sendall(f"{cmd}\r\n")

                        # Handle commands
                        if cmd == "enable":
                            enabled = True
                            channel.sendall(_prompt(True))
                        elif cmd in ("exit", "logout", "quit"):
                            channel.sendall("\r\nlogout\r\n")
                            channel.close()
                            return
                        elif "terminal width" in cmd:
                            # Netmiko arista_eos waits for "Width set to" in response
                            import re as _re
                            m = _re.search(r"terminal width (\d+)", cmd)
                            w = m.group(1) if m else "32767"
                            channel.sendall(f"\r\nWidth set to {w}{_prompt(enabled)}")
                        elif "terminal length 0" in cmd:
                            channel.sendall(f"\r\nPagination disabled{_prompt(enabled)}")
                        elif any(x in cmd for x in ("terminal length", "terminal monitor")):
                            channel.sendall(_prompt(enabled))
                        elif cmd == "show version":
                            channel.sendall(f"\r\n{SHOW_VERSION}{_prompt(enabled)}")
                        elif "show ip interface brief" in cmd:
                            channel.sendall(f"\r\n{SHOW_IP_INT_BRIEF}{_prompt(enabled)}")
                        elif "show interfaces switchport" in cmd:
                            channel.sendall(f"\r\n{SHOW_INTERFACES_SWITCHPORT}{_prompt(enabled)}")
                        elif "show interfaces" in cmd and "brief" not in cmd:
                            channel.sendall(f"\r\n{SHOW_INTERFACES}{_prompt(enabled)}")
                        elif "show vlan" in cmd:
                            channel.sendall(f"\r\n{SHOW_VLAN}{_prompt(enabled)}")
                        elif "show mac address-table" in cmd:
                            channel.sendall(f"\r\n{SHOW_MAC_TABLE}{_prompt(enabled)}")
                        else:
                            channel.sendall(f"\r\n% Invalid input detected{_prompt(enabled)}")
                    else:
                        buf += char
            else:
                time.sleep(0.02)
    except Exception as e:
        print(f"[mock-ceos] Session error: {e}", flush=True)
    finally:
        transport.close()


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 22))
    sock.listen(20)
    print(f"[mock-ceos] Arista EOS mock SSH server listening on :22 (hostname={HOSTNAME})", flush=True)

    while True:
        try:
            client, addr = sock.accept()
            print(f"[mock-ceos] Connection from {addr}", flush=True)
            t = threading.Thread(target=handle_client, args=(client,), daemon=True)
            t.start()
        except Exception as e:
            print(f"[mock-ceos] Accept error: {e}", flush=True)


if __name__ == "__main__":
    main()
