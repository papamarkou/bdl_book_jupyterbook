from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from latex_normalize import normalize_latex  # noqa: E402


def test_legacy_em_normalization_does_not_match_emph() -> None:
    source = r"\mathbb{V}\textrm{\emph{ar}}[X]"
    converted = normalize_latex(source)
    assert converted == r"\operatorname{Var}[X]"
    assert r"\emph{ph{ar}}" not in converted


def test_nested_legacy_em_is_flattened() -> None:
    source = r"{\em Outer {\em inner} text.}"
    converted = normalize_latex(source)
    assert converted == r"\emph{Outer inner text.}"
