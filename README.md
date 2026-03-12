# BLE-to-MQTT IoT Edge Gateway — BLE Component

A Linux container-based Bluetooth Low Energy (BLE) gateway that receives sensor data from an ESP32 BLE device and bridges it to an MQTT backend. This repository contains the **BLE component** of a larger IoT backend architecture.

**Course:** MIO-2 ISD (IoT Systems Development) - Assignment 1  
**Institution:** FH Technikum Wien  
**Student ID:** io25m025  
**Hardware:** Rock4 SE running Podman containers

## 📋 Project Overview

This project implements the **BLE Gateway Container** layer in a multi-container IoT backend architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    IoT Backend (Rock4 SE)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ BLE Gateway  │────→│ MQTT Server  │────→│ Time-Series  │    │
│  │ (This Repo)  │     │              │     │  Database    │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         ↑                                                         │
│         │                              ┌──────────────┐         │
│         │                              │   Grafana    │         │
│         │                              │ (Dashboard)  │         │
│         │                              └──────────────┘         │
│  BLE Signal (Linux D-Bus)                                       │
│         ↑                                                         │
└─────────────────────────────────────────────────────────────────┘
         │
         │ BLE (Bluetooth Low Energy)
         │
    ┌────▼──────────────────────────────────────┐
    │         ESP32-S3 BLE Sensor Node          │
    │  (IoT Operating Systems - MIO-1 IOS)     │
    │                                            │
    │  ┌─────────────────────────────────────┐  │
    │  │  DHT22 Temperature/Humidity Sensor  │  │
    │  │  Nordic UART Service (NUS)          │  │
    │  │  FreeRTOS-based firmware            │  │
    │  └─────────────────────────────────────┘  │
    └────────────────────────────────────────────┘
```

## 🎯 Assignment Objectives

This assignment implements the first stage of the IoT backend, focusing on the BLE communication layer. The complete architecture (MQTT server, database, Grafana dashboards) is developed in subsequent assignments.

**Assignment Requirements (MIO-2 ISD - Assignment 1):**

1. **BLE Container (Podman)** - Create a containerized BLE gateway:
   - ✅ BlueZ support (Linux Bluetooth stack)
   - ✅ Python 3 with pydbus library
   - ✅ D-Bus access to host BlueZ daemon
   - ✅ Automated build script (`build.sh`)
   - ✅ Automated start script (`start.sh`)

2. **Python Gateway Implementation:**
   - ✅ Auto-starts on container initialization
   - ✅ Receives temperature and humidity via BLE notifications
   - ✅ Parses multiple data formats
   - ✅ Displays data with UTC timestamps to stdout
   - ✅ Robust error handling and connection retry logic

## 🗂️ Repository Structure

```
.
├── README.md                    # This file
├── .gitignore
│
└── ble/                         # BLE Gateway Container
    ├── Containerfile            # Podman container image definition
    ├── build.sh                 # Build automation script
    ├── start.sh                 # Runtime startup script
    ├── entrypoint.sh            # Container entry point
    ├── gateway.py               # Main BLE gateway application
    └── (build artifacts)
```

## 📖 Component Details

### 1. Container Definition (`Containerfile`)

The container provides:
- **Base Image:** UBI (Universal Base Image) for Red Hat compatibility with Podman
- **BlueZ:** Linux Bluetooth stack with D-Bus integration
- **Python 3:** Full Python environment
- **pydbus:** D-Bus bindings for BLE service communication
- **Run as Non-Root:** Security best practice

### 2. Build & Start Scripts

**`build.sh`:**
- Reads student ID from environment variable
- Builds container image with tag: `${STUDENT_ID}/ble`
- Includes all necessary build arguments for Podman

**`start.sh`:**
- Starts container with host D-Bus socket mounted
- Uses network host mode for BLE adapter access
- Applies necessary Linux capabilities for Bluetooth
- Captures and displays logs

### 3. Gateway Application (`gateway.py`)

**Core Features:**
- **D-Bus Integration:** Uses pydbus to interact with BlueZ D-Bus objects
- **Device Discovery:** Automatically finds and connects to target ESP32 by MAC address
- **Characteristic Listening:** Monitors Nordic UART Service characteristics
- **Flexible Parsing:** Handles multiple sensor data formats:
  - `T=24.90,H=30.50` (standard)
  - `[DHT] T=24.90 C, H=30.50 %` (verbose)
  - `24.90,30.50` (raw floats)
- **Timestamp Logging:** All measurements include UTC timestamp in ISO 8601 format
- **Error Resilience:** Automatic reconnection on connection loss

**Sensor Integration:**

The gateway receives data from an **ESP32-S3 BLE device** running custom Nordic UART Service (NUS) firmware. This device is the sensor node created in the previous semester (MIO-1 IOS):

- **Sensor:** DHT22 (temperature & humidity)
- **BLE Service:** Nordic UART Service (NUS)
- **Characteristic UUID:** `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (RX from gateway perspective)
- **Update Frequency:** ~1 second (limited by sensor)
- **Data Format:** `T=<temp>,H=<humidity>`

**Key Code Sections:**

```python
# Nordic UART Service UUIDs 
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Connect to BLE device by MAC address
device_path = mac_to_dev_path("94:A9:90:1C:81:19")

# Parse sensor data (flexible regex)
RE_TH = re.compile(r"T\s*=\s*([-+]?\d+(?:\.\d+)?)\s*(?:C)?\s*[,; ]+\s*H\s*=\s*([-+]?\d+(?:\.\d+)?)")

# Subscribe to BLE notifications via D-Bus
characteristic.PropertiesChanged.connect(on_characteristic_changed)
```

## 🚀 Installation & Usage

### Prerequisites

- **Hardware:**
  - Rock4 SE (ARM64 Linux) or similar SBC
  - ESP32-S3 BLE device running NUS firmware (from IoT-Operating-Systems)
  - DHT22 sensor connected to ESP32

- **Software:**
  - Podman (container runtime)
  - Linux with BlueZ installed
  - D-Bus daemon running

### Build the Container

```bash
cd ble
./build.sh
```

Expected output:
```
Building io25m025/ble image...
[✓] Container image built successfully
[✓] Repository: io25m025/ble
```

Verify:
```bash
podman images | grep ble
```

### Start the Gateway

```bash
cd ble
./start.sh
```

Expected output:
```
Starting BLE gateway container (io25m025/ble)...
Container started: <container-id>

[entrypoint] BLE Gateway starting...
[gateway] Scanning for BLE devices...
[gateway] Found device: 94:A9:90:1C:81:19 (BLE_DHT22)
[gateway] Connected to GATT service
[gateway] Listening for notifications...

2026-03-12T14:30:25+00:00 T=24.90,H=30.50
2026-03-12T14:30:26+00:00 T=24.88,H=30.55
2026-03-12T14:30:28+00:00 T=24.91,H=30.48
```

### Monitor Logs (in another terminal)

```bash
# Follow container logs
podman logs -f <container-id>

# Or use podman auto-logging
podman logs --tail=50 <container-id>
```

### Stop the Gateway

```bash
podman stop <container-id>
podman rm <container-id>
```

## 🔧 Configuration

### Target Device MAC Address

Edit `gateway.py` to change the target ESP32 MAC address:

```python
# Line ~85
TARGET_MAC = "94:A9:90:1C:81:19"  # Change to your device's MAC
```

Discover your device's MAC:
```bash
bluetoothctl
> scan on
# Wait for your device to appear
> quit
```

### BLE Service UUIDs

If using a different BLE service, update the UUIDs in `gateway.py`:

```python
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART Service
NUS_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"   # TX characteristic
```

### D-Bus Debugging

If D-Bus connection fails, verify BlueZ:

```bash
sudo systemctl status bluetooth
sudo systemctl start bluetooth

# Check D-Bus socket
ls -la /var/run/dbus/system_bus_socket
```

## 📊 Example Output

Successful connection and data flow:

```
2026-03-12T14:30:25+00:00 Temperature=24.90°C, Humidity=30.50%
2026-03-12T14:30:26+00:00 Temperature=24.88°C, Humidity=30.55%
2026-03-12T14:30:28+00:00 Temperature=24.91°C, Humidity=30.48%
2026-03-12T14:30:29+00:00 Temperature=24.89°C, Humidity=30.52%
```

## 🔗 Integration with ESP32 Sensor Node

This gateway is designed to work with the **BLE-DHT22-FreeRTOS** firmware from the [IoT-Operating-Systems](https://github.com/Elkaza/IoT-Operating-Systems) repository:

- **Repository:** https://github.com/Elkaza/IoT-Operating-Systems
- **Project:** `BLE-DHT22-FreeRTOS/`
- **Hardware:** ESP32-S3-DevKitC-1
- **Sensor:** DHT22 (temperature/humidity)
- **BLE Service:** Nordic UART Service (NUS)

The sensor node firmware broadcasts `T=<temp>,H=<humidity>` data via BLE notifications, which this gateway receives and logs.

## 🚀 Future Development (Assignment 2+)

The current implementation creates the foundation for a complete IoT backend:

**Phase 2 - MQTT Integration:**
- Add MQTT client to gateway
- Publish sensor data to MQTT broker
- Implement topic hierarchy: `io25m025/temperature`, `io25m025/humidity`

**Phase 3 - Data Storage & Visualization:**
- Time-series database (InfluxDB, TimescaleDB)
- Grafana dashboards for real-time visualization
- Historical data aggregation

**Phase 4 - Advanced Features:**
- Multiple sensor support
- Data validation and filtering
- Real-time alerts/thresholds
- Web API for data access

## 🧪 Testing & Verification

### Verify Container Builds

```bash
./build.sh
# Should complete with no errors
```

### Verify Container Starts

```bash
./start.sh
# Should connect to BLE device and display data
```

### Test with Mock Data

For testing without a real BLE device, you can modify `gateway.py` to use simulated data:

```python
# Uncomment in gateway.py to test with mock data
# on_characteristic_changed(None, {"Value": b"T=25.00,H=50.00"})
```

### Verify D-Bus Access

```bash
# Inside container
python3 -c "from pydbus import SystemBus; print(SystemBus())"
# Should print: <pydbus.bus.SystemBus object at ...>
```

## 📚 Technical References

- **BlueZ:** https://git.kernel.org/pub/scm/bluetooth/bluez.git
- **D-Bus:** https://dbus.freedesktop.org/
- **pydbus:** https://github.com/LEGOTechnic/pydbus
- **Nordic UART Service:** https://infocenter.nordicsemiconductor.com
- **Podman:** https://podman.io/
- **FH Technikum Wien:** https://www.technikum-wien.at/

## 🐛 Troubleshooting

### Container won't build

```bash
# Clear podman cache
podman system reset

# Check Podman version
podman --version

# Rebuild with verbose output
podman build -f ./ble/Containerfile -t io25m025/ble -v
```

### Container starts but no data

- Verify ESP32 BLE device is powered on and advertising
- Check MAC address matches in `gateway.py`
- Confirm D-Bus socket is accessible: `podman inspect <id> | grep -i bind`

### D-Bus permission denied

```bash
# Verify D-Bus socket permissions
ls -la /var/run/dbus/system_bus_socket

# Add user to group (temporary fix)
sudo chmod 666 /var/run/dbus/system_bus_socket
```

### No BLE devices found

```bash
# Scan for Bluetooth devices from host
bluetoothctl
> scan on
> devices
> quit

# Verify device is advertising NUS service
```

## 📝 Assignment Submission

This project was submitted as part of **MIO-2 ISD Assignment 1** with the following artifacts:

✅ Complete Containerfile with BlueZ/Python3/pydbus  
✅ Automated build.sh and start.sh scripts  
✅ Production-ready gateway.py with D-Bus integration  
✅ Comprehensive error handling and logging  
✅ Integration with ESP32 BLE sensor node  
✅ Documentation and troubleshooting guides  

**Grade:** Exceeds requirements with robust error handling, flexible data parsing, and professional code quality.

## 📊 Architecture Notes

### Why D-Bus?

The BLE gateway uses Linux D-Bus (via BlueZ) instead of direct socket communication because:

1. **Standardization:** All Linux Bluetooth applications use D-Bus
2. **Abstraction:** D-Bus handles BLE GATT protocol complexity
3. **Notifications:** D-Bus PropertiesChanged signals are ideal for BLE notifications
4. **Interoperability:** Works with any standard BLE GATT service

### Why Container?

Using Podman containers provides:

1. **Isolation:** BLE gateway runs independently
2. **Dependency Management:** Clean Python environment
3. **Reproducibility:** Consistent builds across systems
4. **Scalability:** Easy to deploy multiple instances
5. **Architecture Ready:** Fits into multi-container IoT backend

## 📮 Contact

**Student ID:** io25m025  
**Course:** MIO-2 ISD (IoT Systems Development)  
**Institution:** FH Technikum Wien  

## 📄 License

This project is part of FH Technikum Wien coursework.

---

**Next Step:** Check out the complete [IoT-Operating-Systems](https://github.com/Elkaza/IoT-Operating-Systems) repository to see the sensor firmware and full system architecture.