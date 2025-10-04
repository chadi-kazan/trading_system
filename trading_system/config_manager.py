"""Configuration management utilities for the trading system."""

from __future__ import annotations

import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


WEEKDAY_NAMES = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


class ConfigError(Exception):
    """Raised when configuration files are missing or invalid."""


@dataclass
class EmailConfig:
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    recipient: str
    use_tls: bool = True


@dataclass
class RiskManagementConfig:
    max_positions: int
    individual_stop: float
    portfolio_stop: float
    sector_limits: Dict[str, float]
    position_sizing: str = "equal_weight"


@dataclass
class StrategyWeightsConfig:
    zanger: float
    canslim: float
    trend_following: float
    livermore: float

    def total_weight(self) -> float:
        return sum(asdict(self).values())

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class DataSourcesConfig:
    yahoo_finance: bool
    alpha_vantage_key: Optional[str]
    fred_api_key: Optional[str] = None
    sec_edgar_enabled: bool = False
    cache_days: int = 7


@dataclass
class UniverseCriteriaConfig:
    market_cap_min: int
    market_cap_max: int
    min_daily_volume: int
    max_spread: float
    min_float: int
    target_sectors: list[str] = field(default_factory=list)
    exchange_whitelist: list[str] = field(default_factory=lambda: ["NYSE", "NASDAQ", "AMEX"])


@dataclass
class StorageConfig:
    price_cache_dir: Path
    universe_dir: Path
    signal_dir: Path
    portfolio_dir: Path


@dataclass
class FundamentalsValidationConfig:
    enabled: bool = True
    min_universe_size: int = 10
    sample_size: Optional[int] = None
    persist_snapshot: bool = True
    fail_on_breach: bool = True


@dataclass
class FundamentalsRefreshAutomationConfig:
    enabled: bool
    frequency: str
    time: str
    day: Optional[str] = None
    include_russell: bool = False
    limit: Optional[int] = None
    throttle: float = 12.0
    validation: FundamentalsValidationConfig = field(default_factory=FundamentalsValidationConfig)


@dataclass
class AutomationConfig:
    scan_frequency: str
    scan_day: str
    scan_time: str
    timezone: str
    send_reports: bool = True
    fundamentals_refresh: FundamentalsRefreshAutomationConfig = field(
        default_factory=lambda: FundamentalsRefreshAutomationConfig(
            enabled=False,
            frequency="daily",
            time="00:00",
        )
    )


@dataclass
class TradingSystemConfig:
    email: EmailConfig
    risk_management: RiskManagementConfig
    strategy_weights: StrategyWeightsConfig
    data_sources: DataSourcesConfig
    universe_criteria: UniverseCriteriaConfig
    storage: StorageConfig
    automation: AutomationConfig

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConfigManager:
    """Loads and validates configuration data from files and environment variables."""

    def __init__(
        self,
        default_path: Path | str = Path("config/default_settings.json"),
        user_path: Path | str = Path("config/settings.local.json"),
        env_prefix: str = "TS_",
    ) -> None:
        self.default_path = Path(default_path)
        self.user_path = Path(user_path)
        self.env_prefix = env_prefix
        self._cached_config: Optional[TradingSystemConfig] = None

    def load(self, force_reload: bool = False) -> TradingSystemConfig:
        """Load configuration from defaults, user overrides, and environment."""
        if self._cached_config is not None and not force_reload:
            return self._cached_config

        base_config = self._load_default_config()
        merged_config = self._merge_user_overrides(base_config)
        merged_config = self._apply_env_overrides(merged_config)

        config = self._build_config(merged_config)
        self._validate_config(config)
        self._ensure_storage_paths(config)

        self._cached_config = config
        return config

    def clear_cache(self) -> None:
        """Clear the cached configuration instance."""
        self._cached_config = None

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    def _load_default_config(self) -> Dict[str, Any]:
        if not self.default_path.exists():
            raise ConfigError(f"Default configuration file not found: {self.default_path}")

        with self.default_path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"Unable to parse default configuration: {exc}") from exc

    def _merge_user_overrides(self, base: Dict[str, Any]) -> Dict[str, Any]:
        data = json.loads(json.dumps(base))  # deep copy via JSON to keep types JSON-compatible
        if self.user_path.exists():
            with self.user_path.open("r", encoding="utf-8") as handle:
                try:
                    overrides = json.load(handle)
                except json.JSONDecodeError as exc:
                    raise ConfigError(f"Unable to parse user configuration: {exc}") from exc
            self._deep_merge(data, overrides)
        return data

    def _apply_env_overrides(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = json.loads(json.dumps(data))
        prefix_len = len(self.env_prefix)
        for key, value in os.environ.items():
            if not key.startswith(self.env_prefix):
                continue
            path_parts = key[prefix_len:].lower().split("__")
            parsed_value = self._parse_env_value(value)
            self._set_nested_value(result, path_parts, parsed_value)
        return result

    # ------------------------------------------------------------------
    # Build dataclasses
    # ------------------------------------------------------------------
    def _build_config(self, data: Dict[str, Any]) -> TradingSystemConfig:
        try:
            email = EmailConfig(**data["email"])
            risk = RiskManagementConfig(**data["risk_management"])
            weights = StrategyWeightsConfig(**data["strategy_weights"])
            sources = DataSourcesConfig(**data["data_sources"])
            universe = UniverseCriteriaConfig(**data["universe_criteria"])
            storage = StorageConfig(**{
                key: Path(value)
                for key, value in data["storage"].items()
            })
            automation_data = data["automation"]
            fundamentals_data = automation_data.get("fundamentals_refresh", {})
            validation_data = fundamentals_data.get("validation", {})

            sample_size_value = validation_data.get("sample_size")
            sample_size = int(sample_size_value) if sample_size_value is not None else None

            validation = FundamentalsValidationConfig(
                enabled=validation_data.get("enabled", True),
                min_universe_size=int(validation_data.get("min_universe_size", 10)),
                sample_size=sample_size,
                persist_snapshot=validation_data.get("persist_snapshot", True),
                fail_on_breach=validation_data.get("fail_on_breach", True),
            )

            limit_value = fundamentals_data.get("limit")
            limit = int(limit_value) if limit_value is not None else None

            fundamentals_refresh = FundamentalsRefreshAutomationConfig(
                enabled=fundamentals_data.get("enabled", False),
                frequency=str(fundamentals_data.get("frequency", "daily")),
                time=str(fundamentals_data.get("time", "22:00")),
                day=fundamentals_data.get("day"),
                include_russell=fundamentals_data.get("include_russell", False),
                limit=limit,
                throttle=float(fundamentals_data.get("throttle", 12.0)),
                validation=validation,
            )

            automation = AutomationConfig(
                scan_frequency=automation_data["scan_frequency"],
                scan_day=automation_data["scan_day"],
                scan_time=automation_data["scan_time"],
                timezone=automation_data["timezone"],
                send_reports=automation_data.get("send_reports", True),
                fundamentals_refresh=fundamentals_refresh,
            )
        except KeyError as exc:
            raise ConfigError(f"Missing required configuration section: {exc}") from exc
        except TypeError as exc:
            raise ConfigError(f"Invalid configuration field: {exc}") from exc

        return TradingSystemConfig(
            email=email,
            risk_management=risk,
            strategy_weights=weights,
            data_sources=sources,
            universe_criteria=universe,
            storage=storage,
            automation=automation,
        )

    # ------------------------------------------------------------------
    # Validation & utilities
    # ------------------------------------------------------------------
    def _validate_config(self, config: TradingSystemConfig) -> None:
        if not (0 < config.risk_management.individual_stop < 1):
            raise ConfigError("individual_stop must be between 0 and 1 (exclusive)")
        if not (0 < config.risk_management.portfolio_stop < 1):
            raise ConfigError("portfolio_stop must be between 0 and 1 (exclusive)")
        if config.risk_management.max_positions <= 0:
            raise ConfigError("max_positions must be greater than zero")

        for name, limit in config.risk_management.sector_limits.items():
            if not 0 < limit <= 1:
                raise ConfigError(f"Sector limit for {name} must be within (0, 1].")

        weight_total = config.strategy_weights.total_weight()
        if not 0.99 <= weight_total <= 1.01:
            raise ConfigError("Strategy weights must sum to 1.0")

        if config.universe_criteria.market_cap_min >= config.universe_criteria.market_cap_max:
            raise ConfigError("market_cap_min must be less than market_cap_max")

        if config.universe_criteria.max_spread <= 0 or config.universe_criteria.max_spread >= 1:
            raise ConfigError("max_spread must be between 0 and 1")

        if config.data_sources.cache_days <= 0:
            raise ConfigError("cache_days must be positive")

        for path in config.storage.__dict__.values():
            if not isinstance(path, Path):
                raise ConfigError("Storage paths must be valid paths")

        refresh = config.automation.fundamentals_refresh
        frequency = refresh.frequency.lower()
        if frequency not in {"daily", "weekly"}:
            raise ConfigError("automation.fundamentals_refresh.frequency must be 'daily' or 'weekly'")

        if not self._is_valid_time_format(refresh.time):
            raise ConfigError("automation.fundamentals_refresh.time must be HH:MM or HH:MM:SS")

        if refresh.limit is not None and refresh.limit <= 0:
            raise ConfigError("automation.fundamentals_refresh.limit must be positive when set")

        if refresh.throttle < 0:
            raise ConfigError("automation.fundamentals_refresh.throttle must be non-negative")

        validation = refresh.validation
        if validation.sample_size is not None and validation.sample_size <= 0:
            raise ConfigError("automation.fundamentals_refresh.validation.sample_size must be positive when set")

        if validation.min_universe_size < 0:
            raise ConfigError("automation.fundamentals_refresh.validation.min_universe_size must be >= 0")

        if frequency == "weekly":
            day = (refresh.day or config.automation.scan_day or "").strip().lower()
            if not day:
                raise ConfigError("automation.fundamentals_refresh.day or automation.scan_day must be provided for weekly schedules")
            if day not in WEEKDAY_NAMES:
                raise ConfigError("automation.fundamentals_refresh.day must be a valid weekday name")

    def _ensure_storage_paths(self, config: TradingSystemConfig) -> None:
        for path in config.storage.__dict__.values():
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> None:
        for key, value in overrides.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        value = value.strip()
        if not value:
            return value
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def _is_valid_time_format(value: str) -> bool:
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _set_nested_value(target: Dict[str, Any], path_parts: list[str], value: Any) -> None:
        current = target
        for part in path_parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return the currently cached configuration as a dictionary."""
        config = self.load()
        return config.as_dict()


def _print_summary() -> None:
    manager = ConfigManager()
    config = manager.load(force_reload=True)
    summary = {
        "email": {
            "smtp_server": config.email.smtp_server,
            "recipient": config.email.recipient,
        },
        "max_positions": config.risk_management.max_positions,
        "strategy_weights": config.strategy_weights.as_dict(),
        "storage": {key: str(value) for key, value in config.storage.__dict__.items()},
    }
    print(json.dumps(summary, indent=2))


def _test_missing_file() -> bool:
    try:
        ConfigManager(default_path=Path("config/does_not_exist.json")).load()
    except ConfigError:
        return True
    return False


if __name__ == "__main__":
    print("Configuration preview:")
    _print_summary()
    print("\nMissing file check passed:", _test_missing_file())


__all__ = [
    "ConfigError",
    "ConfigManager",
    "TradingSystemConfig",
    "EmailConfig",
    "RiskManagementConfig",
    "StrategyWeightsConfig",
    "DataSourcesConfig",
    "UniverseCriteriaConfig",
    "StorageConfig",
    "FundamentalsValidationConfig",
    "FundamentalsRefreshAutomationConfig",
    "AutomationConfig",
]
