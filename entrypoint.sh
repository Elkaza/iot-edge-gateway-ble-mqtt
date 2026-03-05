#!/bin/sh
set -eu

echo "[entrypoint] starting BLE gateway..."
exec python3 /app/gateway.py
