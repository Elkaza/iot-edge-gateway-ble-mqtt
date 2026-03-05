cat > ~/ble_container/gateway.py <<'EOF'
#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime, timezone

from pydbus import SystemBus
from gi.repository import GLib

BLUEZ = "org.bluez"

OM_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

ADAPTER_IFACE = "org.bluez.Adapter1"
DEV_IFACE = "org.bluez.Device1"
CHRC_IFACE = "org.bluez.GattCharacteristic1"

# Nordic UART Service (your ESP32 firmware uses this)
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
# In your setup, notifications come from 6e400003...
NUS_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Accept both formats:
# 1) "[DHT] T=24.90 C, H=30.50 %"
# 2) "T=24.90,H=30.50"
# 3) "24.90,30.50"
RE_TH = re.compile(r"T\s*=\s*([-+]?\d+(?:\.\d+)?)\s*(?:C)?\s*[,; ]+\s*H\s*=\s*([-+]?\d+(?:\.\d+)?)",
                   re.IGNORECASE)
RE_FLOATS = re.compile(r"[-+]?\d+(?:\.\d+)?")

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def mac_to_dev_path(mac: str) -> str:
    return "/org/bluez/hci0/dev_" + mac.strip().upper().replace(":", "_")

def bytes_to_text(v):
    try:
        return bytes(v).decode("utf-8", errors="replace").strip()
    except Exception:
        return str(list(v))

def get_managed_objects(bus):
    m = bus.get(BLUEZ, "/")
    return m.GetManagedObjects()

def find_adapter_path(objects):
    for path, ifaces in objects.items():
        if ADAPTER_IFACE in ifaces:
            return path
    return None

def find_device_path(objects, mac):
    target = mac_to_dev_path(mac)
    if target in objects:
        return target
    mac_l = mac.strip().lower()
    for path, ifaces in objects.items():
        d = ifaces.get(DEV_IFACE)
        if not d:
            continue
        if str(d.get("Address", "")).lower() == mac_l:
            return path
    return None

def start_discovery(bus, adapter_path):
    adapter = bus.get(BLUEZ, adapter_path)
    try:
        print(f"{now()} Starting discovery on {adapter_path} ...", flush=True)
        adapter.StartDiscovery()
    except Exception as e:
        print(f"{now()} Discovery start failed (can be ok): {e}", flush=True)

def stop_discovery(bus, adapter_path):
    adapter = bus.get(BLUEZ, adapter_path)
    try:
        adapter.StopDiscovery()
    except Exception:
        pass

def wait_for_device(bus, mac, timeout_s=12):
    deadline = GLib.get_monotonic_time() + int(timeout_s * 1_000_000)
    while GLib.get_monotonic_time() < deadline:
        objects = get_managed_objects(bus)
        dev_path = find_device_path(objects, mac)
        if dev_path:
            return dev_path, objects
        GLib.usleep(300_000)
    return None, None

def connect_with_retries(dev, tries=12):
    delays = [0.6,0.8,1.0,1.4,2.0,2.8,3.6,4.5,5.5,6.5,7.5,8.5]
    for i in range(1, tries + 1):
        try:
            print(f"{now()} Connecting (attempt {i}/{tries})...", flush=True)
            dev.Connect()
            return True
        except Exception as e:
            print(f"{now()} Connect error: {e}", flush=True)
            try:
                dev.Disconnect()
            except Exception:
                pass
            GLib.usleep(int(delays[min(i-1, len(delays)-1)] * 1_000_000))
    return False

def wait_services_resolved(dev, timeout_s=25):
    deadline = GLib.get_monotonic_time() + int(timeout_s * 1_000_000)
    while GLib.get_monotonic_time() < deadline:
        try:
            if bool(dev.Get(DEV_IFACE, "ServicesResolved")):
                return True
        except Exception:
            pass
        GLib.usleep(400_000)
    return False

def find_notify_char(objects, dev_path):
    best = None
    any_notify = None
    for path, ifaces in objects.items():
        if not path.startswith(dev_path + "/"):
            continue
        ch = ifaces.get(CHRC_IFACE)
        if not ch:
            continue
        uuid = str(ch.get("UUID", "")).lower()
        flags = set(ch.get("Flags", []))

        if uuid == NUS_NOTIFY_UUID:
            best = path

        if any_notify is None and (("notify" in flags) or ("indicate" in flags)):
            any_notify = path

    return best or any_notify

def parse_temp_hum(text: str):
    # Try "T=.. H=.." first
    m = RE_TH.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Otherwise, try first two floats in the string
    floats = RE_FLOATS.findall(text)
    if len(floats) >= 2:
        return float(floats[0]), float(floats[1])

    return None, None

def main():
    print(f"{now()} GATEWAY v3 (single-notify: parses T & H from payload)", flush=True)

    mac = os.environ.get("SENSOR_MAC", "").strip()
    if not mac:
        print("ERROR: SENSOR_MAC not set", file=sys.stderr)
        sys.exit(2)

    bus = SystemBus()
    objects = get_managed_objects(bus)

    adapter_path = find_adapter_path(objects)
    if not adapter_path:
        print("ERROR: No Bluetooth adapter found on DBus.", file=sys.stderr)
        sys.exit(10)

    dev_path, objects = wait_for_device(bus, mac, timeout_s=2)
    if not dev_path:
        start_discovery(bus, adapter_path)
        dev_path, objects = wait_for_device(bus, mac, timeout_s=12)
        stop_discovery(bus, adapter_path)

    if not dev_path:
        print(f"ERROR: BLE device {mac} not found (not discovered).", file=sys.stderr)
        sys.exit(3)

    print(f"{now()} Found device at {dev_path}", flush=True)
    dev = bus.get(BLUEZ, dev_path)

    if not connect_with_retries(dev, tries=12):
        print("ERROR: Could not connect after retries.", file=sys.stderr)
        sys.exit(4)

    if not wait_services_resolved(dev, timeout_s=25):
        print("ERROR: Services not resolved (timeout).", file=sys.stderr)
        sys.exit(5)

    objects = get_managed_objects(bus)
    char_path = find_notify_char(objects, dev_path)
    if not char_path:
        print("ERROR: No notify characteristic found under the device.", file=sys.stderr)
        sys.exit(6)

    print(f"{now()} Using notify characteristic: {char_path}", flush=True)
    ch = bus.get(BLUEZ, char_path)

    latest_t = None
    latest_h = None

    def on_props_changed(sender, object, iface, signal, params):
        nonlocal latest_t, latest_h
        iface_name, changed, _invalidated = params
        if iface_name != CHRC_IFACE:
            return
        if "Value" not in changed:
            return

        text = bytes_to_text(changed["Value"])
        t, h = parse_temp_hum(text)

        # If payload doesn't contain both, still show raw (helps debugging ESP32)
        if t is None or h is None:
            print(f"{now()}  raw='{text}'  (missing T/H in payload)", flush=True)
            return

        latest_t, latest_h = t, h
        print(f"{now()}  temp={latest_t:.2f}C  hum={latest_h:.2f}%", flush=True)

    bus.subscribe(
        iface=PROPS_IFACE,
        signal="PropertiesChanged",
        object=char_path,
        signal_fired=on_props_changed,
    )

    try:
        ch.StartNotify()
        print(f"{now()} Notify started", flush=True)
    except Exception as e:
        print(f"ERROR: StartNotify failed: {e}", file=sys.stderr)
        sys.exit(7)

    GLib.MainLoop().run()

if __name__ == "__main__":
    main()
EOF
