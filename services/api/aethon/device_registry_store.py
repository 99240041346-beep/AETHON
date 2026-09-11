"""Compatibility export for the PostgreSQL-backed device registry."""
from app.device_registry_store import DeviceRegistryError, DeviceRegistryStore, StoredDevice

__all__ = ["DeviceRegistryError", "DeviceRegistryStore", "StoredDevice"]
