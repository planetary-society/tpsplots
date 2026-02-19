"""Controller for Planetary Exploration Budget Dataset tabs.

Dynamically generates a controller method for each tab in the
PlanetaryBudgetDataSource, allowing YAML configs to reference any
mission or budget tab by name::

    data:
      source: planetary_mission_budget.cassini

    data:
      source: planetary_mission_budget.europa_clipper

    data:
      source: planetary_mission_budget.fy_2026
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.planetary_budget_data_source import PlanetaryBudgetDataSource

# Tabs that are metadata/non-data and should not get controller methods
_EXCLUDED_TABS: frozenset[str] = frozenset({"Introduction", "Charts"})


def _tab_to_method_name(tab: str) -> str:
    """Convert a tab name to a valid snake_case Python identifier.

    Examples:
        "Cassini"           → "cassini"
        "Europa Clipper"    → "europa_clipper"
        "FY 2026"           → "fy_2026"
        "Pioneer 10 & 11"  → "pioneer_10_11"
        "MPL/MCO"           → "mpl_mco"
        "OSIRIS-REx"        → "osiris_rex"
        "FY 1976 TQ"        → "fy_1976_tq"
    """
    name = tab.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def _make_tab_method(tab_name: str):
    """Factory: create a controller method that loads a specific tab."""

    def method(self: PlanetaryMissionBudgetController) -> dict[str, Any]:
        return self._load_tab(tab_name)

    method.__name__ = _tab_to_method_name(tab_name)
    method.__doc__ = f"Load data from the '{tab_name}' tab."
    return method


class PlanetaryMissionBudgetController(ChartController):
    """Controller with dynamically generated methods for each planetary budget tab.

    Each tab in ``PlanetaryBudgetDataSource.TAB_GID_LOOKUP`` (except metadata
    tabs) becomes a callable method on this class. The method loads the tab's
    data and returns a standard result dict for YAML consumption.

    Use ``available_methods()`` to see the full mapping of method names to tab
    names.
    """

    # Populated by the class-level loop below
    _METHOD_TO_TAB: ClassVar[dict[str, str]] = {}

    def _load_tab(self, tab: str) -> dict[str, Any]:
        """Load a planetary budget tab and return a YAML-ready result dict.

        Applies NNSI inflation adjustment to all detected monetary columns,
        creating ``{col}_adjusted_nnsi`` variants for each.

        Args:
            tab: Canonical tab name (e.g. "Cassini", "FY 2026").

        Returns:
            Dict with ``"data"`` (DataFrame), column arrays, inflation-adjusted
            columns, and ``"metadata"`` (including ``inflation_adjusted_year``).
        """
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        source = PlanetaryBudgetDataSource(tab)
        df = source.data()

        # Apply NNSI inflation adjustment to all monetary columns
        monetary_cols = PlanetaryBudgetDataSource._detect_monetary_columns(df)
        if monetary_cols and "Fiscal Year" in df.columns:
            inflation_config = InflationAdjustmentConfig(
                nnsi_columns=monetary_cols,
                fiscal_year_column="Fiscal Year",
            )
            df = InflationAdjustmentProcessor(inflation_config).process(df)

        result = self._build_result_dict(df)

        metadata: dict[str, Any] = {
            "tab_name": source.tab_name,
            "source": "The Planetary Society, Planetary Exploration Budget Dataset",
        }
        if "inflation_target_year" in df.attrs:
            metadata["inflation_adjusted_year"] = int(df.attrs["inflation_target_year"])
        result["metadata"] = metadata
        return result

    @classmethod
    def available_methods(cls) -> dict[str, str]:
        """Return mapping of method names to canonical tab names."""
        return dict(cls._METHOD_TO_TAB)

    def __dir__(self) -> list[str]:
        """Include generated method names in dir() output."""
        return sorted(set(super().__dir__()) | set(self._METHOD_TO_TAB))


# ── Generate methods for each tab at class creation time ──

_seen_names: dict[str, str] = {}  # method_name → tab_name (for collision detection)

for _tab_name in PlanetaryBudgetDataSource.TAB_GID_LOOKUP:
    if _tab_name in _EXCLUDED_TABS:
        continue

    _method_name = _tab_to_method_name(_tab_name)

    # Collision detection
    if _method_name in _seen_names:
        raise RuntimeError(
            f"Tab name collision: '{_tab_name}' and '{_seen_names[_method_name]}' "
            f"both map to method name '{_method_name}'"
        )
    _seen_names[_method_name] = _tab_name

    setattr(PlanetaryMissionBudgetController, _method_name, _make_tab_method(_tab_name))

PlanetaryMissionBudgetController._METHOD_TO_TAB = dict(_seen_names)

# Clean up module-level temporaries
del _seen_names, _tab_name, _method_name
