"""Tests for GroupedBarTransformProcessor."""

import pandas as pd
import pytest

from tpsplots.processors.grouped_bar_transform_processor import (
    GroupedBarTransformConfig,
    GroupedBarTransformProcessor,
)


class TestGroupedBarTransformProcessor:
    """Tests for GroupedBarTransformProcessor."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with grouped bar inputs."""
        return pd.DataFrame(
            {
                "Account": ["Science", "Exploration", "Space Ops"],
                "FY 2025 Enacted": [7, 8, 5],
                "FY 2026 Request": [7.5, 9, 4],
                "Appropriated": [7.2, 8.5, 4.5],
            }
        )

    def test_builds_categories_and_groups(self, sample_df):
        """Processor should populate categories and groups attrs."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted", "FY 2026 Request"],
            group_labels=["FY25", "FY26"],
        )
        result = GroupedBarTransformProcessor(config).process(sample_df)

        assert result.attrs["categories"] == ["Science", "Exploration", "Space Ops"]
        assert result.attrs["groups"] == [
            {"label": "FY25", "values": [7, 8, 5]},
            {"label": "FY26", "values": [7.5, 9, 4]},
        ]
        assert result.attrs["groups_all"] == result.attrs["groups"]

    def test_defaults_group_labels_to_column_names(self, sample_df):
        """When group_labels is None, labels should be column names."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted", "FY 2026 Request"],
        )
        result = GroupedBarTransformProcessor(config).process(sample_df)

        labels = [group["label"] for group in result.attrs["groups"]]
        assert labels == ["FY 2025 Enacted", "FY 2026 Request"]

    def test_sorting_by_column_descending(self, sample_df):
        """sort_by should order categories by the specified column descending."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted"],
            sort_by="FY 2026 Request",
            sort_descending=True,
        )
        result = GroupedBarTransformProcessor(config).process(sample_df)

        assert result.attrs["categories"] == ["Exploration", "Science", "Space Ops"]

    def test_sorting_by_column_ascending(self, sample_df):
        """sort_descending=False should order categories ascending."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted"],
            sort_by="FY 2026 Request",
            sort_descending=False,
        )
        result = GroupedBarTransformProcessor(config).process(sample_df)

        assert result.attrs["categories"] == ["Space Ops", "Science", "Exploration"]

    def test_group_sets(self, sample_df):
        """Processor should build named group sets in attrs."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted", "FY 2026 Request", "Appropriated"],
            group_sets={"pair": [0, 2]},
        )
        result = GroupedBarTransformProcessor(config).process(sample_df)

        assert "groups_pair" in result.attrs
        assert result.attrs["groups_pair"] == [
            {"label": "FY 2025 Enacted", "values": [7, 8, 5]},
            {"label": "Appropriated", "values": [7.2, 8.5, 4.5]},
        ]

    def test_missing_category_column_raises(self, sample_df):
        """Missing category column should raise KeyError."""
        config = GroupedBarTransformConfig(
            category_column="Department",
            value_columns=["FY 2025 Enacted"],
        )

        with pytest.raises(KeyError, match="Category column 'Department' not found"):
            GroupedBarTransformProcessor(config).process(sample_df)

    def test_missing_value_column_raises(self, sample_df):
        """Missing value column should raise KeyError."""
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["Missing Column"],
        )

        with pytest.raises(KeyError, match="Value column 'Missing Column' not found"):
            GroupedBarTransformProcessor(config).process(sample_df)
