"""Helpers for sharing configuration/state with the dashboard API."""

from __future__ import annotations

from functools import lru_cache

from trading_system.config_manager import ConfigManager, TradingSystemConfig


@lru_cache(maxsize=1)
def get_config_manager() -> ConfigManager:
    """Return a cached ConfigManager instance."""

    return ConfigManager()


@lru_cache(maxsize=1)
def get_config() -> TradingSystemConfig:
    """Load and cache the trading system configuration."""

    manager = get_config_manager()
    return manager.load()


__all__ = ["get_config", "get_config_manager"]
