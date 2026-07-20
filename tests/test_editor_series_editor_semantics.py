"""Static checks for the shared series-array write path (lib/seriesArrays.js).

When a per-series style property starts life as a YAML scalar (e.g.
``markersize: 12`` applying to every series), editing one series must not
discard the scalar for the untouched rows: the write path must seed its
working array with the scalar repeated for ALL series before applying the
single edit. The machinery lives in ``writeSeriesValue`` and is consumed by
SeriesEditor; these checks guard the scalar-expansion branch so it does not
regress back to the bare scalar-discard, and that SeriesEditor actually
delegates to the shared module.
"""

from tests.conftest import read_source as _read

_LIB = "tpsplots/editor/static/js/lib/seriesArrays.js"


def test_write_seeds_working_array_from_scalar():
    src = _read(_LIB)
    # Scalar (non-array, non-nullish) seeds the array for every series.
    assert "existing !== undefined && existing !== null" in src
    assert "new Array(seriesCount).fill(existing)" in src


def test_write_preserves_array_and_undefined_branches():
    src = _read(_LIB)
    # Array values are still copied through unchanged (no mutation).
    assert "if (Array.isArray(existing)) {" in src
    assert "arr = [...existing];" in src
    # Undefined/null still starts from an empty working array.
    assert "arr = [];" in src


def test_series_table_delegates_to_shared_module():
    src = _read("tpsplots/editor/static/js/components/SeriesTable.js")
    assert "writeSeriesValue" in src
    assert "seriesValueAt" in src


def test_reorder_permutes_every_correlated_array():
    """Reordering a series must move its styles/labels with it."""
    src = _read("tpsplots/editor/static/js/components/SeriesTable.js")
    assert "permuteCorrelated" in src
    assert "spliceCorrelated" in src
