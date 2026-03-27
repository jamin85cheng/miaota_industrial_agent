"""
PLC data collection module.

This module keeps the original public surface area while fixing connection-state
handling and adding compatibility aliases used by legacy entrypoints.
"""

from __future__ import annotations

import random
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.utils.thread_safe import ConnectionGuard, SafeValue

try:
    import snap7

    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    snap7 = None
    logger.warning("snap7 is not installed; S7 collection is unavailable")

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder

    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    ModbusTcpClient = None
    Endian = None
    BinaryPayloadDecoder = None
    logger.warning("pymodbus is not installed; Modbus collection is unavailable")


class PLCCollector:
    """Collect realtime data from S7, Modbus TCP, or a simulated source."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plc_type = config.get("type", "s7").lower()
        self.scan_interval = config.get("scan_interval", 10)
        self.tags: List[Dict[str, Any]] = self._normalize_tags(config.get("tags", []))
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []

        self._client_guard = ConnectionGuard(f"PLC-{self.plc_type}")
        self._running = SafeValue(False)
        self._thread: Optional[threading.Thread] = None
        self._reconnect_attempts = SafeValue(0)
        self._max_reconnect_attempts = int(config.get("max_reconnect_attempts", 5))
        self._reconnect_delay = int(config.get("reconnect_delay", 5))

        logger.info(f"PLCCollector initialized for type={self.plc_type}")

    @property
    def client(self):
        return self._client_guard.client

    @property
    def is_connected(self) -> bool:
        return self._client_guard.is_connected

    @is_connected.setter
    def is_connected(self, value: bool):
        if not value:
            self._client_guard.disconnect(self._cleanup_client)

    def _normalize_tags(self, tags: Any) -> List[Dict[str, Any]]:
        if isinstance(tags, dict):
            normalized: List[Dict[str, Any]] = []
            for tag_id, config in tags.items():
                if isinstance(config, dict):
                    normalized.append(
                        {
                            "tag_id": tag_id,
                            "address": config.get("plc_address")
                            or config.get("address")
                            or tag_id,
                            "data_type": config.get("data_type", "FLOAT"),
                            **config,
                        }
                    )
                else:
                    normalized.append(
                        {
                            "tag_id": tag_id,
                            "address": config,
                            "data_type": "FLOAT",
                        }
                    )
            return normalized

        if isinstance(tags, list):
            normalized = []
            for tag in tags:
                if isinstance(tag, dict):
                    normalized.append(tag)
                else:
                    normalized.append(
                        {"tag_id": str(tag), "address": str(tag), "data_type": "FLOAT"}
                    )
            return normalized

        return []

    def set_tags(self, tags: Any):
        self.tags = self._normalize_tags(tags)

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def connect(self) -> bool:
        if self.is_connected:
            return True

        if self.plc_type == "s7":
            return self._client_guard.connect(self._build_s7_client)
        if self.plc_type == "modbus":
            return self._client_guard.connect(self._build_modbus_client)
        if self.plc_type == "simulated":
            return self._client_guard.connect(lambda: object())

        logger.error(f"Unsupported PLC type: {self.plc_type}")
        return False

    def _build_s7_client(self):
        if not SNAP7_AVAILABLE:
            raise RuntimeError("snap7 is not installed")

        host = self.config.get("host", "192.168.1.100")
        port = self.config.get("port", 102)
        rack = self.config.get("rack", 0)
        slot = self.config.get("slot", 1)

        client = snap7.client.Client()
        client.connect(host, rack, slot, port)
        if not client.is_connected():
            raise RuntimeError(f"Failed to connect to S7 PLC at {host}:{port}")
        return client

    def _build_modbus_client(self):
        if not MODBUS_AVAILABLE:
            raise RuntimeError("pymodbus is not installed")

        host = self.config.get("host", "192.168.1.101")
        port = self.config.get("port", 502)
        client = ModbusTcpClient(host, port=port)
        if not client.connect():
            raise RuntimeError(f"Failed to connect to Modbus device at {host}:{port}")
        return client

    def _cleanup_client(self, client):
        try:
            if self.plc_type == "s7" and hasattr(client, "disconnect"):
                client.disconnect()
            elif self.plc_type == "modbus" and hasattr(client, "close"):
                client.close()
        except Exception as exc:
            logger.warning(f"Failed to cleanly disconnect PLC client: {exc}")

    def disconnect(self):
        self._running.set(False)
        self._client_guard.disconnect(self._cleanup_client)

    def read_tag(self, tag_config: Dict[str, Any]) -> Optional[Any]:
        if not self.is_connected and not self.connect():
            logger.warning("PLC is not connected")
            return None

        address = tag_config.get("address", "")
        data_type = str(tag_config.get("data_type", "FLOAT")).upper()

        try:
            if self.plc_type == "s7":
                return self._read_s7_tag(address, data_type)
            if self.plc_type == "modbus":
                return self._read_modbus_tag(address, data_type)
            if self.plc_type == "simulated":
                return self._read_simulated_tag(tag_config, data_type)
        except Exception as exc:
            logger.error(f"Failed to read tag {address}: {exc}")

        return None

    def _read_s7_tag(self, address: str, data_type: str) -> Optional[Any]:
        client = self.client
        if client is None:
            return None

        if address.startswith("DB"):
            parts = address.split(".")
            db_number = int(parts[0][2:])
            offset = int(parts[1][3:]) if len(parts) > 1 and "D" in parts[1] else 0

            if data_type == "FLOAT":
                data = client.db_read(db_number, offset, 4)
                return int.from_bytes(data, byteorder="big", signed=False)
            if data_type == "INT":
                data = client.db_read(db_number, offset, 2)
                return int.from_bytes(data, byteorder="big", signed=True)
            if data_type == "BOOL":
                data = client.db_read(db_number, offset, 1)
                return bool(data[0] & 1)

        if address.startswith("M"):
            offset = int("".join(ch for ch in address if ch.isdigit()) or "0")
            size = 2 if data_type == "INT" else 4
            data = client.read_area(snap7.types.Areas.MK, 0, offset, size)
            if data_type == "BOOL":
                return bool(data[0] & 1)
            return int.from_bytes(data, byteorder="big", signed=data_type == "INT")

        logger.warning(f"Unsupported S7 address format: {address}")
        return None

    def _read_modbus_tag(self, address: str, data_type: str) -> Optional[Any]:
        client = self.client
        if client is None:
            return None

        register_address = max(int(address) - 40001, 0)

        if data_type == "FLOAT":
            result = client.read_holding_registers(register_address, 2, slave=1)
            if result.isError():
                return None
            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers,
                byteorder=Endian.Big,
                wordorder=Endian.Big,
            )
            return decoder.decode_32bit_float()

        if data_type == "INT":
            result = client.read_holding_registers(register_address, 1, slave=1)
            if result.isError():
                return None
            return result.registers[0]

        if data_type == "BOOL":
            result = client.read_coils(register_address, 1, slave=1)
            if result.isError():
                return None
            return result.bits[0]

        logger.warning(f"Unsupported Modbus data type: {data_type}")
        return None

    def _read_simulated_tag(self, tag_config: Dict[str, Any], data_type: str) -> Any:
        if "value" in tag_config:
            return tag_config["value"]
        if data_type == "BOOL":
            return random.choice([True, False])
        if data_type == "INT":
            return random.randint(0, 100)
        return round(random.uniform(0, 100), 2)

    def read_all_tags(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for tag in self.tags:
            tag_id = tag.get("tag_id") or tag.get("address")
            value = self.read_tag(tag)
            values[tag_id] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "quality": "good" if value is not None else "bad",
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "values": values,
        }

    def start_continuous_collection(self, callback: Callable[[Dict[str, Any]], None]):
        self.register_callback(callback)
        self.start_collection()

    def start_collection(
        self,
        addresses: Optional[Any] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        if addresses is not None:
            self.set_tags(addresses)
        if callback is not None:
            self.register_callback(callback)
        if self._running.get():
            logger.warning("Collection is already running")
            return

        self._running.set(True)
        self._reconnect_attempts.set(0)
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Collection loop started with interval={self.scan_interval}s")

    def _collection_loop(self):
        while self._running.get():
            try:
                if not self.is_connected and not self._try_reconnect():
                    time.sleep(self._reconnect_delay)
                    continue

                data = self.read_all_tags()
                self._reconnect_attempts.set(0)

                for callback in list(self.callbacks):
                    try:
                        callback(data)
                    except Exception as exc:
                        logger.error(f"Collection callback failed: {exc}")

                time.sleep(self.scan_interval)
            except Exception as exc:
                logger.error(f"Collection loop error: {exc}")
                self.disconnect()
                time.sleep(self._reconnect_delay)

    def _try_reconnect(self) -> bool:
        attempts = self._reconnect_attempts.get()
        if attempts >= self._max_reconnect_attempts:
            logger.error(
                f"Reconnect attempts exceeded maximum ({self._max_reconnect_attempts})"
            )
            self._reconnect_attempts.set(0)
            return False

        delay = min(self._reconnect_delay * (2**attempts), 60)
        self._reconnect_attempts.set(attempts + 1)
        logger.info(
            f"Reconnect attempt {attempts + 1}/{self._max_reconnect_attempts} in {delay}s"
        )
        time.sleep(delay)
        return self.connect()

    def stop_continuous_collection(self):
        self.stop_collection()

    def stop_collection(self):
        self._running.set(False)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self.disconnect()
        logger.info("Collection loop stopped")

    def reconnect(self):
        self.disconnect()
        time.sleep(1)
        return self.connect()


if __name__ == "__main__":
    sample_config = {
        "type": "simulated",
        "scan_interval": 2,
        "tags": [
            {"tag_id": "TAG_DO_001", "address": "MW100", "data_type": "FLOAT"},
            {"tag_id": "TAG_PH_001", "address": "MW104", "data_type": "FLOAT"},
            {"tag_id": "TAG_PUMP_001", "address": "Q0.0", "data_type": "BOOL"},
        ],
    }

    collector = PLCCollector(sample_config)

    def on_data_received(data: Dict[str, Any]):
        print(data)

    collector.start_continuous_collection(on_data_received)
    time.sleep(5)
    collector.stop_collection()
