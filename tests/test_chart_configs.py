"""Tests for per-chart-type Pydantic config models.

Covers:
- YAML regression: all example YAML files validate against the discriminated union
- Per-model acceptance/rejection
- Escape hatches (matplotlib_config, pywaffle_config)
- Template reference validation
- JSON schema generation
- Discriminator dispatch
- Mixin model_config enforcement
"""

import json
from glob import glob

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from tpsplots.models import (
    CONFIG_REGISTRY,
    BarChartConfig,
    ChartConfig,
    DonutChartConfig,
    GroupedBarChartConfig,
    LineChartConfig,
    LineSubplotsChartConfig,
    LollipopChartConfig,
    ScatterChartConfig,
    StackedBarChartConfig,
    USMapPieChartConfig,
    WaffleChartConfig,
    YAMLChartConfig,
)
from tpsplots.models.mixins import (
    AxisMixin,
    BarStylingMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    SortMixin,
    TickFormatMixin,
    ValueDisplayMixin,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_adapter = TypeAdapter(ChartConfig)

YAML_EXAMPLES = sorted(glob("yaml/examples/**/*.yaml", recursive=True))


# ---------------------------------------------------------------------------
# 1. YAML regression — every example file must validate
# ---------------------------------------------------------------------------
class TestYAMLRegression:
    @pytest.mark.parametrize("yaml_file", YAML_EXAMPLES, ids=lambda p: p.split("/")[-1])
    def test_existing_yaml_validates(self, yaml_file):
        """Every YAML example in the repo must validate against YAMLChartConfig."""
        with open(yaml_file) as f:
            raw = yaml.safe_load(f)
        config = YAMLChartConfig(**raw)
        # The chart field should be dispatched to a concrete config model
        assert type(config.chart).__name__.endswith("Config")


# ---------------------------------------------------------------------------
# 2. Per-model acceptance
# ---------------------------------------------------------------------------
class TestModelAcceptance:
    def test_line_accepts_all_fields(self):
        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            x="{{year}}",
            y=["{{val1}}", "{{val2}}"],
            color=["red", "blue"],
            linestyle=["-", "--"],
            linewidth=[2, 3],
            labels=["A", "B"],
            grid=True,
            legend={"loc": "upper right"},
            scale="billions",
            direct_line_labels={"position": "right", "fontsize": 10},
            fiscal_year_ticks=True,
            hlines=[1000, 2000],
            export_data="{{export_df}}",
        )
        assert config.type == "line"
        d = config.model_dump(exclude_none=True)
        assert d["grid"] is True
        assert d["scale"] == "billions"

    def test_scatter_inherits_line(self):
        config = ScatterChartConfig(
            type="scatter",
            output="test",
            title="T",
            x="{{x}}",
            y="{{y}}",
            marker="o",
        )
        assert config.type == "scatter"
        assert isinstance(config, LineChartConfig)

    def test_bar_accepts_all_fields(self):
        config = BarChartConfig(
            type="bar",
            output="test",
            title="T",
            categories="{{cats}}",
            values="{{vals}}",
            show_values=True,
            value_format="${:,.0f}",
            sort_by="value",
            sort_ascending=False,
        )
        assert config.type == "bar"
        d = config.model_dump(exclude_none=True)
        assert d["show_values"] is True

    def test_donut_accepts_all_fields(self):
        config = DonutChartConfig(
            type="donut",
            output="test",
            title="T",
            values="{{Budget}}",
            labels="{{Directorate}}",
            show_percentages=True,
            hole_size=0.6,
            center_text="NASA",
            center_color="white",
            label_distance=1.1,
        )
        assert config.type == "donut"

    def test_waffle_accepts_all_fields(self):
        config = WaffleChartConfig(
            type="waffle",
            output="test",
            title="T",
            values="{{values}}",
            labels="{{labels}}",
            colors=["blue", "gray"],
            vertical=True,
            starting_location="SW",
            interval_ratio_x=0.1,
            interval_ratio_y=0.1,
        )
        assert config.type == "waffle"

    def test_lollipop_accepts_marker_fields(self):
        config = LollipopChartConfig(
            type="lollipop",
            output="test",
            title="T",
            categories="{{cats}}",
            start_values="{{start}}",
            end_values="{{end}}",
            start_marker_style="o",
            end_marker_style="D",
            start_marker_size=8,
            end_marker_size=10,
            line_width=2,
            value_labels=True,
        )
        assert config.type == "lollipop"

    def test_stacked_bar_accepts_fields(self):
        config = StackedBarChartConfig(
            type="stacked_bar",
            output="test",
            title="T",
            categories="{{cats}}",
            values=["{{v1}}", "{{v2}}"],
            labels="{{labels}}",
            colors="{{colors}}",
            value_threshold=100,
        )
        assert config.type == "stacked_bar"

    def test_grouped_bar_accepts_fields(self):
        config = GroupedBarChartConfig(
            type="grouped_bar",
            output="test",
            title="T",
            categories="{{cats}}",
            groups=[{"values": "{{g1}}"}],
            labels=["G1"],
            show_values=True,
        )
        assert config.type == "grouped_bar"

    def test_us_map_pie_accepts_fields(self):
        config = USMapPieChartConfig(
            type="us_map_pie",
            output="test",
            title="T",
            pie_data="{{data}}",
            pie_size_column="total",
            show_state_boundaries=True,
        )
        assert config.type == "us_map_pie"

    def test_line_subplots_accepts_fields(self):
        config = LineSubplotsChartConfig(
            type="line_subplots",
            output="test",
            title="T",
            subplot_data="{{data}}",
            grid_shape=[2, 3],
            shared_x=True,
            shared_y=True,
        )
        assert config.type == "line_subplots"


# ---------------------------------------------------------------------------
# 3. Rejection — unknown fields
# ---------------------------------------------------------------------------
class TestRejection:
    def test_rejects_unknown_field_on_line(self):
        with pytest.raises(ValidationError):
            LineChartConfig(type="line", output="t", title="t", bogus_field=True)

    def test_rejects_unknown_field_on_bar(self):
        with pytest.raises(ValidationError):
            BarChartConfig(type="bar", output="t", title="t", bogus_field=True)

    def test_rejects_unknown_field_on_donut(self):
        with pytest.raises(ValidationError):
            DonutChartConfig(type="donut", output="t", title="t", bogus_field=True)

    def test_rejects_unknown_field_on_waffle(self):
        with pytest.raises(ValidationError):
            WaffleChartConfig(type="waffle", output="t", title="t", bogus_field=True)

    def test_discriminator_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            _adapter.validate_python({"type": "invalid_type", "output": "t", "title": "t"})

    @pytest.mark.parametrize(
        ("config_cls", "alias_field", "alias_value"),
        [
            (LineChartConfig, "df", "{{frame}}"),
            (LineChartConfig, "c", "red"),
            (LineChartConfig, "ls", "--"),
            (LineChartConfig, "lw", 2.5),
            (LineChartConfig, "ms", 8),
            (LineChartConfig, "label", ["A", "B"]),
            (LineChartConfig, "horizontal_lines", [100, 200]),
            (LineChartConfig, "x_axis_format", ",.0f"),
            (LineChartConfig, "y_axis_format", ",.0f"),
            (ScatterChartConfig, "label", ["A", "B"]),
            (ScatterChartConfig, "ls", "--"),
            (GroupedBarChartConfig, "bar_width", 0.4),
            (GroupedBarChartConfig, "x_axis_format", ",.0f"),
            (GroupedBarChartConfig, "y_axis_format", ",.0f"),
            (LollipopChartConfig, "line_style", ":"),
            (LollipopChartConfig, "x_axis_format", ",.0f"),
            (LollipopChartConfig, "y_axis_format", ",.0f"),
            (BarChartConfig, "x_axis_format", ",.0f"),
            (BarChartConfig, "y_axis_format", ",.0f"),
            (StackedBarChartConfig, "x_axis_format", ",.0f"),
            (StackedBarChartConfig, "y_axis_format", ",.0f"),
            (LineSubplotsChartConfig, "x_axis_format", ",.0f"),
            (LineSubplotsChartConfig, "y_axis_format", ",.0f"),
        ],
        ids=lambda case: f"{case.__name__}:{case}" if hasattr(case, "__name__") else str(case),
    )
    def test_rejects_removed_alias_fields(self, config_cls, alias_field, alias_value):
        with pytest.raises(ValidationError):
            config_cls(type=config_cls.model_fields["type"].default, output="t", title="t", **{alias_field: alias_value})


# ---------------------------------------------------------------------------
# 4. Escape hatches
# ---------------------------------------------------------------------------
class TestEscapeHatches:
    def test_matplotlib_config_accepted(self):
        config = DonutChartConfig(
            type="donut",
            output="test",
            title="T",
            values="{{v}}",
            matplotlib_config={"pctdistance": 0.8, "shadow": True},
        )
        assert config.matplotlib_config == {"pctdistance": 0.8, "shadow": True}

    def test_pywaffle_config_accepted(self):
        config = WaffleChartConfig(
            type="waffle",
            output="test",
            title="T",
            values="{{v}}",
            pywaffle_config={"icon_style": "solid", "icon_legend": True},
        )
        assert config.pywaffle_config == {"icon_style": "solid", "icon_legend": True}

    def test_matplotlib_config_on_line(self):
        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            matplotlib_config={"zorder": 5},
        )
        assert config.matplotlib_config == {"zorder": 5}


# ---------------------------------------------------------------------------
# 5. Template ref validation
# ---------------------------------------------------------------------------
class TestTemplateRefs:
    def test_template_ref_accepted_in_numeric_fields(self):
        """Fields that accept float|str should accept {{ref}} strings."""
        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            tick_size="{{ref}}",
            label_size="{{ref}}",
        )
        assert config.tick_size == "{{ref}}"

    def test_numeric_fields_reject_non_template_strings(self):
        """Numeric-or-ref fields should reject plain strings like 'banana'."""
        with pytest.raises(ValidationError):
            LineChartConfig(
                type="line",
                output="test",
                title="T",
                tick_size="banana",
            )

        with pytest.raises(ValidationError):
            LineChartConfig(
                type="line",
                output="test",
                title="T",
                label_size="large-ish",
            )

        with pytest.raises(ValidationError):
            LineChartConfig(
                type="line",
                output="test",
                title="T",
                max_xticks="many",
            )

    def test_numeric_fields_accept_template_refs(self):
        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            tick_size="{{tick_size_ref}}",
            label_size="{{label_size_ref}}",
            max_xticks="{{max_ticks_ref}}",
        )
        assert config.tick_size == "{{tick_size_ref}}"
        assert config.label_size == "{{label_size_ref}}"
        assert config.max_xticks == "{{max_ticks_ref}}"

    def test_template_ref_accepted_in_list_fields(self):
        """Labels that can be either list[str] or a single template ref."""
        config = WaffleChartConfig(
            type="waffle",
            output="test",
            title="T",
            values="{{values}}",
            labels="{{labels}}",
        )
        assert config.labels == "{{labels}}"

    def test_ylim_accepts_dates(self):
        """YAML parses 1958-01-01 as datetime.date — xlim/ylim must accept them."""
        import datetime

        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            xlim=[datetime.date(1958, 1, 1), datetime.date(2030, 1, 1)],
            ylim=[0, 80_000_000_000],
        )
        assert len(config.xlim) == 2


# ---------------------------------------------------------------------------
# 6. JSON schema generation
# ---------------------------------------------------------------------------
class TestSchemaGeneration:
    def test_discriminated_union_schema(self):
        schema = _adapter.json_schema()
        schema_str = json.dumps(schema)
        assert "discriminator" in schema_str or "oneOf" in schema_str or "anyOf" in schema_str

    def test_schema_has_all_chart_types(self):
        schema = _adapter.json_schema()
        schema_str = json.dumps(schema)
        for chart_type in CONFIG_REGISTRY:
            assert chart_type in schema_str, f"Chart type '{chart_type}' missing from schema"


# ---------------------------------------------------------------------------
# 7. Discriminator dispatch
# ---------------------------------------------------------------------------
class TestDiscriminatorDispatch:
    @pytest.mark.parametrize("chart_type,config_cls", CONFIG_REGISTRY.items())
    def test_each_config_has_type_literal(self, chart_type, config_cls):
        """Each config's type literal matches its registry key."""
        minimal = {"type": chart_type, "output": "t", "title": "t"}
        instance = _adapter.validate_python(minimal)
        assert isinstance(instance, config_cls)
        assert instance.type == chart_type

    def test_yaml_chart_config_dispatches(self):
        """YAMLChartConfig.chart field dispatches to correct model."""
        config = YAMLChartConfig(
            data={"source": "test.csv"},
            chart={
                "type": "bar",
                "output": "test_bar",
                "title": "Test",
            },
        )
        assert isinstance(config.chart, BarChartConfig)


# ---------------------------------------------------------------------------
# 8. Mixin model_config enforcement
# ---------------------------------------------------------------------------
MIXIN_CLASSES = [
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    SortMixin,
    ValueDisplayMixin,
    BarStylingMixin,
]


class TestMixinSafety:
    @pytest.mark.parametrize("mixin", MIXIN_CLASSES, ids=lambda c: c.__name__)
    def test_no_mixin_sets_model_config(self, mixin):
        """Mixins must NOT set model_config with values — Pydantic v2 MRO bug (#9992).

        Pydantic v2 always adds an empty ``model_config = {}`` to every
        BaseModel subclass's ``__dict__``. The real danger is a mixin
        explicitly setting keys like ``extra`` or ``populate_by_name``,
        which would silently override ChartConfigBase's config.
        """
        mc = mixin.__dict__.get("model_config", {})
        assert not mc, (
            f"{mixin.__name__} has model_config={mc}. Only ChartConfigBase should set model_config."
        )

    def test_base_sets_extra_forbid(self):
        assert ChartConfigBase.model_config.get("extra") == "forbid"

    def test_base_sets_populate_by_name(self):
        assert ChartConfigBase.model_config.get("populate_by_name") is True


# ---------------------------------------------------------------------------
# 9. Series overrides (dynamic series_N keys)
# ---------------------------------------------------------------------------
class TestSeriesOverrides:
    def test_series_n_keys_collected(self):
        """series_0, series_1, etc. should be collected into series_overrides."""
        config = LineChartConfig(
            type="line",
            output="test",
            title="T",
            series_0={"color": "red", "linestyle": "--"},
            series_1={"color": "blue"},
        )
        assert config.series_overrides is not None
        assert 0 in config.series_overrides
        assert 1 in config.series_overrides
        assert config.series_overrides[0]["color"] == "red"

    def test_no_series_keys_means_none(self):
        config = LineChartConfig(type="line", output="test", title="T")
        assert config.series_overrides is None
