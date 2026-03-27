"""Lightweight exports for the data package."""

from __future__ import annotations

from .collector import PLCCollector

try:
    from .storage import TimeSeriesStorage
except Exception:
    TimeSeriesStorage = None

try:
    from .preprocessor import DataPreprocessor
except Exception:
    DataPreprocessor = None

__all__ = ["PLCCollector", "TimeSeriesStorage", "DataPreprocessor"]
