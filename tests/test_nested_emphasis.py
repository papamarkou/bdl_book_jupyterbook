from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from latex_normalize import normalize_latex  # noqa: E402


def test_nested_legacy_emphasis_is_flattened() -> None:
    source = (
        r"{\em This estimator is consistent, which is not the case for a naive "
        r"{\em unweighted} average.}"
    )
    converted = normalize_latex(source)

    assert converted == (
        r"\emph{This estimator is consistent, which is not the case for a naive "
        r"unweighted average.}"
    )
    assert converted.count(r"\emph{") == 1
    assert r"{\em" not in converted
