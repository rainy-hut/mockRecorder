from __future__ import annotations

import threading
from collections import defaultdict

from app.constants import Mode


class RuntimeContext:
    def __init__(
        self,
        mode: str = Mode.OFF,
        profile_name: str = "default",
        test_item_code: str = "DEFAULT_TEST",
        variant_name: str = "normal",
        product_name: str = "MM",
        process_station: str = "FT1-MP1",
        product_code: str = "03020001",
        tu_name: str = "UNSET",
    ):
        self._lock = threading.Lock()
        self.mode = mode
        self.current_profile_name = profile_name
        self.current_test_item_code = test_item_code
        self.current_variant_name = variant_name
        self.current_product_name = product_name
        self.current_process_station = process_station
        self.current_product_code = product_code
        self.current_tu_name = tu_name
        self.record_call_counter = defaultdict(int)
        self.replay_call_counter = defaultdict(int)
        self.round_robin_counter = defaultdict(int)

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return {
                "mode": self.mode,
                "profile_name": self.current_profile_name,
                "test_item_code": self.current_test_item_code,
                "variant_name": self.current_variant_name,
                "product_name": self.current_product_name,
                "process_station": self.current_process_station,
                "product_code": self.current_product_code,
                "tu_name": self.current_tu_name,
            }

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self.mode = mode

    def set_current_profile(self, profile_name: str) -> None:
        with self._lock:
            self.current_profile_name = profile_name

    def set_current_test_item(self, test_item_code: str) -> None:
        with self._lock:
            self.current_test_item_code = test_item_code

    def set_current_variant(self, variant_name: str) -> None:
        with self._lock:
            self.current_variant_name = variant_name

    def set_scene(self, product_name: str, process_station: str, product_code: str) -> None:
        with self._lock:
            self.current_product_name = product_name
            self.current_process_station = process_station
            self.current_product_code = product_code

    def set_current_tu_name(self, tu_name: str) -> None:
        with self._lock:
            self.current_tu_name = tu_name

    def update_from_notice(self, data: dict[str, str]) -> None:
        with self._lock:
            self.current_product_name = data.get("productName") or data.get("product_name") or self.current_product_name
            self.current_process_station = data.get("processStation") or data.get("process_station") or self.current_process_station
            self.current_product_code = data.get("productCode") or data.get("product_code") or self.current_product_code
            self.current_tu_name = (
                data.get("testItem")
                or data.get("test_item")
                or data.get("currentTestItem")
                or data.get("tuName")
                or data.get("tu_name")
                or self.current_tu_name
            )

    def next_record_call_index(self, profile_name: str, test_item_code: str, instrument_alias: str, request_hash: str) -> int:
        return self._next(self.record_call_counter, profile_name, test_item_code, instrument_alias, request_hash)

    def next_replay_call_index(self, profile_name: str, test_item_code: str, instrument_alias: str, request_hash: str) -> int:
        return self._next(self.replay_call_counter, profile_name, test_item_code, instrument_alias, request_hash)

    def next_round_robin_index(self, profile_name: str, test_item_code: str, instrument_alias: str, request_hash: str) -> int:
        return self._next(self.round_robin_counter, profile_name, test_item_code, instrument_alias, request_hash)

    def reset_replay_counter(self) -> None:
        with self._lock:
            self.replay_call_counter.clear()
            self.round_robin_counter.clear()

    def _next(self, counter: defaultdict, profile_name: str, test_item_code: str, instrument_alias: str, request_hash: str) -> int:
        key = (profile_name, test_item_code, instrument_alias, request_hash)
        with self._lock:
            counter[key] += 1
            return counter[key]

    def next_scene_record_call_index(self, product_name: str, process_station: str, product_code: str, tu_name: str, instrument_alias: str, request_hash: str) -> int:
        return self._next_scene(self.record_call_counter, product_name, process_station, product_code, tu_name, instrument_alias, request_hash)

    def next_scene_replay_call_index(self, product_name: str, process_station: str, product_code: str, tu_name: str, instrument_alias: str, request_hash: str) -> int:
        return self._next_scene(self.replay_call_counter, product_name, process_station, product_code, tu_name, instrument_alias, request_hash)

    def next_scene_round_robin_index(self, product_name: str, process_station: str, product_code: str, tu_name: str, instrument_alias: str, request_hash: str) -> int:
        return self._next_scene(self.round_robin_counter, product_name, process_station, product_code, tu_name, instrument_alias, request_hash)

    def _next_scene(self, counter: defaultdict, product_name: str, process_station: str, product_code: str, tu_name: str, instrument_alias: str, request_hash: str) -> int:
        key = (product_name, process_station, product_code, tu_name, instrument_alias, request_hash)
        with self._lock:
            counter[key] += 1
            return counter[key]
