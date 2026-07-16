"""Static checks for SeriesEditor scalar-seeding in the per-series write path.

When a per-series style property starts life as a YAML scalar (e.g.
``markersize: 12`` applying to every series), editing one series must not
discard the scalar for the untouched rows. The write path in
``handleFieldChange`` must seed its working array with the scalar repeated for
ALL series before applying the single edit; otherwise leading untouched rows
get backfilled from ``NUMERIC_DEFAULTS`` and trailing rows get truncated. These
checks guard the scalar-expansion branch so it does not regress back to the
bare ``: []`` scalar-discard.
"""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_series_editor_seeds_working_array_from_scalar():
    src = _read("tpsplots/editor/static/js/components/SeriesEditor.js")
    # Scalar (non-array, non-nullish) seeds the array for every series.
    assert "const existing = formData[fieldName];" in src
    assert "existing !== undefined && existing !== null" in src
    assert "Array(series.length).fill(existing)" in src


def test_series_editor_preserves_array_and_undefined_branches():
    src = _read("tpsplots/editor/static/js/components/SeriesEditor.js")
    # Array values are still copied through unchanged.
    assert "if (Array.isArray(existing)) {" in src
    assert "currentArray = [...existing];" in src
    # Undefined/null still falls back to the empty-array default-backfill path.
    assert "currentArray = [];" in src
