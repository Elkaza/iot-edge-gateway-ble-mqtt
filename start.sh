#!/bin/sh
set -eu

# run rootful (needed for host bluetooth/dbus access on many setups)
if [ "$(id -u)" -ne 0 ]; then
  exec sudo -E "$0" "$@"
fi

TAG="localhost/mo/ble:latest"
SENSOR_MAC="${SENSOR_MAC:-94:A9:90:1C:81:19}"

exec podman run --rm -it \
  --pull=never \
  --name ble-gateway \
  --network host \
  --privileged \
  -e SENSOR_MAC="$SENSOR_MAC" \
  -e DBUS_SYSTEM_BUS_ADDRESS="unix:path=/run/dbus/system_bus_socket" \
  -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket \
  -v /var/lib/bluetooth:/var/lib/bluetooth \
  "$TAG"
