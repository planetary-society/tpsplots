"""Processor that computes column sums and stores them in DataFrame.attrs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ColumnSumConfig:
    """Configuration for ColumnSumProcessor.

    Attributes:
        columns: Explicit columns to sum. When None, all numeric columns are
            used (excluding columns whose names end with ``'_raw'``).
        exclude: Column names to skip during auto-detection. Ignored when
            ``columns`` is explicitly set.
    """

    columns: list[str] | None = None
    exclude: list[str] = field(default_factory=list)


class ColumnSumProcessor:
    """Compute per-column sums and store in df.attrs without modifying the DataFrame.

    Results are written to ``df.attrs["column_sums"]`` as a ``dict[str, float]``
    so they surface in metadata automatically via
    :meth:`~tpsplots.controllers.chart_controller.ChartController._build_metadata`.

    Example::

        config = ColumnSumConfig(exclude=["Fiscal Year"])
        df = ColumnSumProcessor(config).process(df)
        # df.attrs["column_sums"] == {"Budget": 300.0, "Amount": 500.0}
    """

    def __init__(self, config: ColumnSumConfig) -> None:
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute sums and store in ``df.attrs["column_sums"]``.

        The input DataFrame is not mutated. Sums are stored as floats.
        Non-numeric columns are silently skipped.

        Args:
            df: Input DataFrame.

        Returns:
            Copy of ``df`` with ``df.attrs["column_sums"]`` populated.
        """
        df = df.copy()
        sums: dict[str, float] = {}
        for col in self._resolve_columns(df):
            if col not in df.columns:
                logger.debug("ColumnSumProcessor: skipping missing column '%s'", col)
                continue
            if not pd.api.types.is_numeric_dtype(df[col]):
                logger.debug("ColumnSumProcessor: skipping non-numeric column '%s'", col)
                continue
            sums[col] = float(df[col].sum(skipna=True))
        df.attrs["column_sums"] = sums
        return df

    def _resolve_columns(self, df: pd.DataFrame) -> list[str]:
        """Return the list of columns to sum.

        Uses ``config.columns`` when set; otherwise auto-detects numeric
        columns while honouring the ``exclude`` list and ``_raw`` suffix filter.
        """
        if self.config.columns is not None:
            return self.config.columns
        skip = set(self.config.exclude)
        return [
            col
            for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
            and col not in skip
            and not col.endswith("_raw")
        ]
