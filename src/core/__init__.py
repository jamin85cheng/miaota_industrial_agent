"""Compatibility exports for the core package."""

from __future__ import annotations

from src.rules import RuleEngine

from .label_engine import LabelFactory
from .tag_mapping import TagMapper


class DataPipeline:
    """Placeholder kept for backward compatibility."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "DataPipeline is no longer part of src.core. Update callers to use the "
            "specialized collection and processing modules directly."
        )


LabelEngine = LabelFactory

__all__ = ["DataPipeline", "TagMapper", "LabelEngine", "LabelFactory", "RuleEngine"]
