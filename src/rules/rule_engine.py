"""
Rule evaluation engine.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .rule_parser import RuleParser


class RuleEngine:
    """Evaluate compiled rules and emit alerts."""

    def __init__(
        self,
        config_file: str,
        evaluation_interval: int = 10,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config_file = config_file
        self.runtime_config = config or {}
        self.evaluation_interval = int(
            self.runtime_config.get("evaluation_interval", evaluation_interval)
        )
        self.parser = RuleParser()

        self.rules: List[Dict[str, Any]] = []
        self.compiled_rules: List[Dict[str, Any]] = []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._suppression_lock = threading.Lock()
        self._callback_lock = threading.Lock()

        self.alert_suppression: Dict[str, datetime] = {}
        self.suppression_window_minutes = int(
            self.runtime_config.get("suppression_window_minutes", 15)
        )
        self.alert_callbacks: List[Callable[[List[Dict[str, Any]]], None]] = []

        self.load_rules()

    def load_rules(self):
        with self._lock:
            self.rules = self.parser.parse_rule_file(self.config_file)
            self.compiled_rules = []

            for rule in self.rules:
                if not rule.get("enabled", True):
                    continue
                try:
                    compiled = {**rule, "check_func": self.parser.compile_condition(rule["condition"])}
                    self.compiled_rules.append(compiled)
                except Exception as exc:
                    logger.error(f"Failed to compile rule {rule.get('rule_id', 'UNKNOWN')}: {exc}")

            logger.info(f"Loaded {len(self.compiled_rules)} active rules")

    def reload_rules(self):
        logger.info("Reloading rules")
        self.load_rules()

    def add_rule(self, rule: Dict[str, Any]):
        with self._lock:
            self.rules.append(rule)
            if rule.get("enabled", True):
                rule = {**rule, "check_func": self.parser.compile_condition(rule["condition"])}
                self.compiled_rules.append(rule)

    def evaluate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered_alerts: List[Dict[str, Any]] = []

        for rule in list(self.compiled_rules):
            try:
                if not rule["check_func"](data):
                    continue

                rule_id = rule["rule_id"]
                now = datetime.now()
                if self._is_suppressed(rule_id, now):
                    continue

                alert = self._create_alert(rule, data)
                triggered_alerts.append(alert)
                self._set_suppression(rule_id, now)
            except Exception as exc:
                logger.error(
                    f"Failed to evaluate rule {rule.get('rule_id', 'UNKNOWN')}: {exc}"
                )

        return triggered_alerts

    def _is_suppressed(self, rule_id: str, now: datetime) -> bool:
        with self._suppression_lock:
            until = self.alert_suppression.get(rule_id)
            return until is not None and now < until

    def _set_suppression(self, rule_id: str, now: datetime):
        with self._suppression_lock:
            self.alert_suppression[rule_id] = now + timedelta(
                minutes=self.suppression_window_minutes
            )

    def _create_alert(self, rule: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "alert_id": f"ALERT_{rule['rule_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "rule_name": rule["name"],
            "label": rule.get("label", rule["name"]),
            "description": rule.get("description", ""),
            "severity": rule.get("severity", "medium"),
            "category": rule.get("category", "general"),
            "timestamp": datetime.now().isoformat(),
            "suggested_actions": rule.get("suggested_actions", []),
            "escalation": rule.get("escalation", {}),
            "data_snapshot": self._extract_relevant_data(data, rule),
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
        }

    def _extract_relevant_data(self, data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {}
        metrics = self._extract_metrics_from_condition(rule.get("condition", {}))
        for metric in metrics:
            if metric in data:
                snapshot[metric] = data[metric]
        return snapshot

    def _extract_metrics_from_condition(self, condition: Dict[str, Any]) -> List[str]:
        metrics: List[str] = []
        if "metric" in condition:
            metrics.append(condition["metric"])
        for sub_condition in condition.get("conditions", []):
            metrics.extend(self._extract_metrics_from_condition(sub_condition))
        metrics.extend(condition.get("metrics", []))
        return list(dict.fromkeys(metrics))

    def start_continuous_evaluation(self, data_provider: Callable[[], Dict[str, Any]]):
        if self._running:
            logger.warning("Rule engine is already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._evaluation_loop,
            args=(data_provider,),
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Rule engine started with interval={self.evaluation_interval}s")

    def _evaluation_loop(self, data_provider: Callable[[], Dict[str, Any]]):
        while self._running:
            try:
                alerts = self.evaluate(data_provider())
                if alerts:
                    callbacks = self._get_callbacks()
                    for callback in callbacks:
                        try:
                            callback(alerts)
                        except Exception as exc:
                            logger.error(f"Alert callback failed: {exc}")
                time.sleep(self.evaluation_interval)
            except Exception as exc:
                logger.error(f"Rule evaluation loop failed: {exc}")
                time.sleep(5)

    def stop_evaluation(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Rule engine stopped")

    def add_alert_callback(self, callback: Callable[[List[Dict[str, Any]]], None]):
        with self._callback_lock:
            self.alert_callbacks.append(callback)

    def register_alert_callback(self, callback: Callable[[List[Dict[str, Any]]], None]):
        self.add_alert_callback(callback)

    def _get_callbacks(self) -> List[Callable[[List[Dict[str, Any]]], None]]:
        with self._callback_lock:
            return list(self.alert_callbacks)

    def acknowledge_alert(self, alert_id: str, operator: str):
        logger.info(f"Alert {alert_id} acknowledged by {operator}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return []

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len(self.compiled_rules),
            "suppression_window_minutes": self.suppression_window_minutes,
            "active_suppressions": len(self.alert_suppression),
            "is_running": self._running,
        }


if __name__ == "__main__":
    engine = RuleEngine("config/rules.json", evaluation_interval=5)

    def get_realtime_data():
        import random

        return {
            "TAG_DO_001": random.uniform(1.0, 5.0),
            "TAG_PH_001": random.uniform(6.0, 8.0),
            "TAG_COD_001": random.uniform(50, 150),
            "_history": {
                "TAG_DO_001": [random.uniform(1.0, 5.0) for _ in range(20)]
            },
        }

    def on_alerts_triggered(alerts):
        print(f"Triggered {len(alerts)} alerts")

    engine.register_alert_callback(on_alerts_triggered)
    engine.start_continuous_evaluation(get_realtime_data)
    time.sleep(5)
    print(engine.get_statistics())
    engine.stop_evaluation()
