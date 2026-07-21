"""Tests for the animation config model, defaults resolution, and pipeline warning."""

import logging
from typing import Literal, get_args, get_origin

import pytest
from pydantic import ValidationError

from tpsplots.animation.config import (
    CHOREOGRAPHY,
    DEFAULTS,
    ResolvedAnimation,
    resolve_animation,
)
from tpsplots.models.animation import AnimationConfig
from tpsplots.models.yaml_config import YAMLChartConfig


def _valid_base_config() -> dict:
    """A minimal, valid YAMLChartConfig payload (no animation block)."""
    return {
        "data": {"source": "data/test.csv"},
        "chart": {"type": "bar", "output": "test", "title": "Test"},
    }


# ---------------------------------------------------------------------------
# 1. YAMLChartConfig parses with and without an animation block
# ---------------------------------------------------------------------------


class TestYAMLChartConfigAnimation:
    def test_parses_without_animation(self):
        cfg = YAMLChartConfig(**_valid_base_config())
        assert cfg.animation is None

    def test_parses_with_valid_animation(self):
        payload = _valid_base_config()
        payload["animation"] = {
            "formats": ["square", "landscape"],
            "fps": 30,
            "duration": 3.0,
            "easing": "cubic_out",
            "quality": "draft",
        }
        cfg = YAMLChartConfig(**payload)
        assert cfg.animation is not None
        assert cfg.animation.formats == ["square", "landscape"]
        assert cfg.animation.fps == 30
        assert cfg.animation.easing == "cubic_out"

    def test_animation_fields_default_none(self):
        """All AnimationConfig fields default to None ('unset')."""
        cfg = AnimationConfig()
        for field in AnimationConfig.model_fields:
            assert getattr(cfg, field) is None


# ---------------------------------------------------------------------------
# 2. Typo inside the animation block is rejected (extra="forbid")
# ---------------------------------------------------------------------------


class TestAnimationExtraForbid:
    def test_typo_field_rejected_directly(self):
        with pytest.raises(ValidationError):
            AnimationConfig(fpss=30)

    def test_typo_field_rejected_through_yaml_config(self):
        payload = _valid_base_config()
        payload["animation"] = {"fpss": 30}
        with pytest.raises(ValidationError):
            YAMLChartConfig(**payload)

    def test_fps_bounds_enforced(self):
        with pytest.raises(ValidationError):
            AnimationConfig(fps=0)
        with pytest.raises(ValidationError):
            AnimationConfig(fps=999)


# ---------------------------------------------------------------------------
# 3. resolve_animation precedence: DEFAULTS <- YAML <- CLI
# ---------------------------------------------------------------------------


class TestResolveAnimation:
    def test_all_defaults(self):
        resolved = resolve_animation()
        assert isinstance(resolved, ResolvedAnimation)
        assert resolved.formats == DEFAULTS["formats"]
        assert resolved.fps == DEFAULTS["fps"]
        assert resolved.intro_hold == DEFAULTS["intro_hold"]
        assert resolved.end_hold == DEFAULTS["end_hold"]
        assert resolved.quality == DEFAULTS["quality"]
        assert resolved.duration is None
        assert resolved.stagger is None
        assert resolved.easing is None
        assert resolved.scale == 1

    def test_yaml_overrides_defaults(self):
        resolved = resolve_animation(AnimationConfig(fps=30))
        assert resolved.fps == 30

    def test_cli_overrides_yaml(self):
        resolved = resolve_animation(AnimationConfig(fps=30), fps=24)
        assert resolved.fps == 24

    def test_cli_none_does_not_override_yaml(self):
        """The precedence-bug guard: an unset (None) CLI flag keeps the YAML value."""
        resolved = resolve_animation(AnimationConfig(fps=30), fps=None)
        assert resolved.fps == 30

    def test_yaml_none_field_keeps_default(self):
        resolved = resolve_animation(AnimationConfig(fps=None))
        assert resolved.fps == DEFAULTS["fps"]

    def test_formats_all_expansion(self):
        resolved = resolve_animation(formats="all")
        assert resolved.formats == ("square", "landscape", "portrait")

    def test_formats_list_normalized_to_tuple(self):
        resolved = resolve_animation(AnimationConfig(formats=["landscape", "portrait"]))
        assert resolved.formats == ("landscape", "portrait")

    def test_unknown_format_rejected_with_valid_names(self):
        """CLI/library format strings are validated at the one chokepoint."""
        with pytest.raises(ValueError, match="Unknown video format 'sqare'"):
            resolve_animation(formats="sqare")

    def test_formats_deduped_when_all_overlaps_explicit(self):
        resolved = resolve_animation(formats=["square", "all"])
        assert resolved.formats == ("square", "landscape", "portrait")

    def test_scale_override(self):
        resolved = resolve_animation(scale=2)
        assert resolved.scale == 2

    def test_unknown_cli_kwarg_raises_type_error(self):
        with pytest.raises(TypeError):
            resolve_animation(bogus=1)

    def test_accepts_plain_mapping_yaml_cfg(self):
        """yaml_cfg may be a plain mapping, not only an AnimationConfig."""
        resolved = resolve_animation({"fps": 45})
        assert resolved.fps == 45


# ---------------------------------------------------------------------------
# 4. Easing Literal <-> EASINGS parity (guards against drift)
# ---------------------------------------------------------------------------


def _easing_literal_names() -> set[str]:
    """Extract the string members of AnimationConfig.easing's Literal."""
    annotation = AnimationConfig.model_fields["easing"].annotation
    names: set[str] = set()
    for arg in get_args(annotation):
        if get_origin(arg) is Literal:
            names |= set(get_args(arg))
    return names


def test_easing_literal_matches_easings_registry():
    # Plain import (not importorskip): easing.py must exist at the integration
    # gate, and this test is meant to catch drift between the two vocabularies.
    from tpsplots.animation.easing import EASINGS

    assert _easing_literal_names() == set(EASINGS)


def test_choreography_easings_are_known_names():
    """Every easing name referenced by CHOREOGRAPHY must be a real easing."""
    from tpsplots.animation.easing import EASINGS

    for chart_type, spec in CHOREOGRAPHY.items():
        for key, value in spec.items():
            if "easing" in key:
                assert value in EASINGS, f"{chart_type}.{key} = {value!r} not in EASINGS"


def test_formats_literal_matches_all_formats_and_video_styles():
    """Format vocabulary parity: the Literal, _ALL_FORMATS, and the video device
    styles must agree (adding a format requires updating all three)."""
    from tpsplots.animation.config import _ALL_FORMATS
    from tpsplots.views.chart_view import ChartView

    annotation = AnimationConfig.model_fields["formats"].annotation
    literal_names: set[str] = set()
    for union_member in get_args(annotation):  # list[Literal[...]] | None
        for item_type in get_args(union_member):  # Literal[...] inside list[...]
            if get_origin(item_type) is Literal:
                literal_names |= set(get_args(item_type))
    assert literal_names == set(_ALL_FORMATS)
    assert {f"video_{fmt}" for fmt in _ALL_FORMATS} <= set(ChartView._DEVICE_STYLES)


def test_choreography_covers_animatable_types():
    assert set(CHOREOGRAPHY) == {
        "area_plot",
        "line_plot",
        "scatter_plot",
        "bar_plot",
        "grouped_bar_plot",
        "stacked_bar_plot",
        "lollipop_plot",
    }


# ---------------------------------------------------------------------------
# 5. Unknown top-level YAML key -> warning, config still validates
# ---------------------------------------------------------------------------


class TestTopLevelKeyWarning:
    def test_unknown_top_level_key_warns(self, tmp_path, caplog):
        import yaml as _yaml

        from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

        yaml_path = tmp_path / "typo.yaml"
        yaml_path.write_text(
            _yaml.dump(
                {
                    "data": {"source": "data/test.csv"},
                    "chart": {"type": "bar", "output": "test", "title": "Test"},
                    "animaton": {"fps": 30},  # typo'd top-level key
                }
            ),
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="tpsplots.processors.yaml_chart_processor"):
            processor = YAMLChartProcessor(yaml_path)

        # Config still validates (Pydantic silently drops the unknown key).
        assert processor.config.chart is not None
        # The typo key is named in a warning.
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("animaton" in msg for msg in warnings), warnings

    def test_no_warning_for_known_keys(self, tmp_path, caplog):
        import yaml as _yaml

        from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

        yaml_path = tmp_path / "clean.yaml"
        yaml_path.write_text(
            _yaml.dump(
                {
                    "data": {"source": "data/test.csv"},
                    "chart": {"type": "bar", "output": "test", "title": "Test"},
                    "animation": {"fps": 30},
                }
            ),
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="tpsplots.processors.yaml_chart_processor"):
            YAMLChartProcessor(yaml_path)

        unknown_warnings = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING and "unknown top-level" in r.getMessage().lower()
        ]
        assert unknown_warnings == []
