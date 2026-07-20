"""Round-trip guard: loading an example YAML through the editor session and
saving it unchanged must never alter its semantics.

This is a permanent regression guard for ``EditorSession.save_yaml`` (see
``tpsplots/editor/session.py``): validation is a gate only, the cleaned *raw*
config is dumped (never a ``model_dump``), ``_deep_replace`` skips unchanged
nodes, and protected chart keys (``annotations``, ``figsize``, ...) are grafted
from the file on disk. Together these mean an untouched config saves back to a
semantically identical document.

Every ``yaml/examples/*.yaml`` is exercised. Controller- and URL-backed sources
need network/data access, so they are marked ``integration`` (deselected by the
default ``-m 'not integration'`` addopts); local ``csv:`` examples run normally.
"""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

from tpsplots.editor.session import EditorSession
from tpsplots.processors.resolvers import DataResolver

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "yaml" / "examples"


# ------------------------------------------------------------------
# Collection: one param per example, integration-marked when the data
# source is not a local file the default test run can read offline.
# ------------------------------------------------------------------


def _is_local_source(source: object) -> bool:
    """True when ``source`` is a local file path the default run can read.

    Uses the same parser the resolver uses, so ``csv:``-prefixed and plain
    local file paths classify as ``csv`` (local) while controller dotted paths,
    ``http(s)`` URLs, and Google Sheets links classify as something else.
    """
    if not isinstance(source, str) or not source.strip():
        return False
    try:
        kind, _, _ = DataResolver._parse_source(source)
    except Exception:
        return False
    return kind == "csv"


def _collect_example_params() -> list["pytest.ParameterSet"]:
    """Build one ``pytest.param`` per top-level example YAML.

    ``glob("*.yaml")`` naturally skips ``schema_yaml.example`` (wrong suffix)
    and the ``data/`` subdirectory (not recursive). Each param value is the
    example's path relative to the repo root, resolved back to absolute inside
    the test.
    """
    params: list[pytest.ParameterSet] = []
    for path in sorted(EXAMPLES_DIR.glob("*.yaml")):
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            cfg = None
        data_section = cfg.get("data") if isinstance(cfg, dict) else None
        source = data_section.get("source") if isinstance(data_section, dict) else None
        marks = () if _is_local_source(source) else (pytest.mark.integration,)
        params.append(pytest.param(rel_path, marks=marks, id=path.name))
    return params


_EXAMPLE_PARAMS = _collect_example_params()


# ------------------------------------------------------------------
# Semantic comparator
# ------------------------------------------------------------------


def _as_iso(value: object) -> object:
    """Normalize a ``datetime.date`` to its ISO string; pass anything else."""
    if isinstance(value, date):
        return value.isoformat()
    return value


def _scalars_equal(original: object, new: object, *, in_list: bool) -> bool:
    """Compare two scalars with the documented round-trip exceptions.

    A ``bool`` never equals an ``int`` (Python's ``True == 1`` would hide a
    YAML type flip). Documented exception (b): a ``datetime.date`` and its
    ISO-string form are treated as equal *only* as list items — the save
    pipeline (``_clean_form_data`` -> ``_coerce_date``) re-coerces string list
    items back to dates but leaves scalar mapping values as strings, so a
    top-level scalar date that changes type is a real failure, not an exception.
    """
    if isinstance(original, bool) is not isinstance(new, bool):
        return False
    if original == new:
        return True
    if in_list:
        return _as_iso(original) == _as_iso(new)
    return False


def _semantic_diffs(
    original: object, new: object, path: str = "", *, in_list: bool = False
) -> list[str]:
    """Return human-readable semantic differences between two loaded configs.

    Documented exception (a): a key whose original value was ``""``, ``[]`` or
    ``{}`` may be dropped by ``_clean_form_data`` (legacy editor-form cleanup)
    and is not reported as a difference.
    """
    diffs: list[str] = []
    if isinstance(original, dict) and isinstance(new, dict):
        for key in sorted(set(original) | set(new)):
            child = f"{path}.{key}" if path else key
            if key not in new:
                if original[key] in ("", [], {}):
                    continue  # exception (a): empty form values may be dropped
                diffs.append(f"dropped: {child} (was {original[key]!r})")
            elif key not in original:
                diffs.append(f"added: {child} = {new[key]!r}")
            else:
                diffs += _semantic_diffs(original[key], new[key], child)
    elif isinstance(original, list) and isinstance(new, list):
        if len(original) != len(new):
            diffs.append(f"list length: {path}: {len(original)} -> {len(new)}")
        else:
            for i, (a, b) in enumerate(zip(original, new, strict=True)):
                diffs += _semantic_diffs(a, b, f"{path}[{i}]", in_list=True)
    elif not _scalars_equal(original, new, in_list=in_list):
        diffs.append(f"changed: {path}: {original!r} -> {new!r}")
    return diffs


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestExampleRoundtrip:
    """No-op save of every example preserves semantics and is idempotent."""

    def test_at_least_one_local_example_collected(self):
        """Guard against a vacuous suite if the glob ever stops matching."""
        local = [p for p in _EXAMPLE_PARAMS if not p.marks]
        assert local, "expected at least one local csv example to run by default"

    @pytest.mark.parametrize("rel_path", _EXAMPLE_PARAMS)
    def test_noop_save_preserves_semantics(self, rel_path, tmp_path):
        src = REPO_ROOT / rel_path
        work = tmp_path / src.name
        shutil.copyfile(src, work)
        session = EditorSession(yaml_dir=tmp_path)

        original = yaml.safe_load(work.read_text(encoding="utf-8"))

        # Simulate the frontend JSON hop: the editor ships the config as JSON,
        # so datetime.date values arrive as ISO strings (default=str). This is
        # what actually exercises session._coerce_date on the way back in.
        payload = json.loads(json.dumps(original, default=str))
        session.save_yaml(src.name, payload)

        after_first = work.read_text(encoding="utf-8")
        reloaded = yaml.safe_load(after_first)

        diffs = _semantic_diffs(original, reloaded)
        assert not diffs, "no-op save changed semantics:\n" + "\n".join(diffs)

        # Second-save idempotency. The first save is allowed one-time cosmetic
        # normalization (indent/flow style, a scalar date -> ISO string), so we
        # compare the second save against the *first* save's output, never the
        # untouched source file. Re-loading and re-saving must be a fixed point.
        payload2 = json.loads(json.dumps(reloaded, default=str))
        session.save_yaml(src.name, payload2)
        after_second = work.read_text(encoding="utf-8")
        assert after_second == after_first, "second save was not byte-identical"
