"""Mixin for truncating DataFrame rows at a marker value."""

from __future__ import annotations

import logging
from typing import ClassVar

import pandas as pd

logger = logging.getLogger(__name__)


class TruncateRowsMixin:
    """Mixin providing row-truncation at a marker value in the first column.

    Subclasses set ``TRUNCATE_AT`` to a marker string (or tuple of strings).
    Calling ``_truncate_rows(df)`` drops the first matching row and everything
    after it.

    Example::

        class MySource(TruncateRowsMixin, ...):
            TRUNCATE_AT = "Totals"
    """

    TRUNCATE_AT: ClassVar[str | tuple[str, ...] | list[str] | None] = None

    def _resolve_truncate_markers(self) -> tuple[str, ...]:
        """Resolve the effective truncation markers for this instance.

        The default implementation reads from the ``TRUNCATE_AT`` class
        variable.  Subclasses may override to support constructor-level
        configuration (see ``TabularDataSource``).
        """
        raw = getattr(self.__class__, "TRUNCATE_AT", None)
        if raw is None:
            return ()
        if isinstance(raw, str):
            normalized = raw.strip()
            return (normalized,) if normalized else ()
        return tuple(str(m).strip() for m in raw if str(m).strip())

    def _truncate_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop the first matched marker row and everything after it."""
        markers = self._resolve_truncate_markers()
        return self._apply_truncation(df, markers)

    @staticmethod
    def _apply_truncation(
        df: pd.DataFrame,
        markers: tuple[str, ...],
    ) -> pd.DataFrame:
        """Core truncation logic: case-insensitive first-column match.

        Args:
            df: Input DataFrame.
            markers: Tuple of marker strings to match against.

        Returns:
            DataFrame with matched row and all subsequent rows removed.
        """
        if not markers or df.empty or df.columns.size == 0:
            return df

        normalized_markers = {m.lower() for m in markers}
        first_col = df.columns[0]
        first_col_vals = df[first_col].astype(str).str.strip().str.lower()
        match_indices = df.index[first_col_vals.isin(normalized_markers)]

        if len(match_indices) == 0:
            return df

        return df.loc[: match_indices[0]].iloc[:-1].copy()
