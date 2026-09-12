from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from convert_authors import latex_to_text  # noqa: E402
from latex_normalize import normalize_latex  # noqa: E402
from text_normalize import normalize_tex_text_accents  # noqa: E402


def test_tex_text_accents_support_braced_and_unbraced_forms() -> None:
    source = r'na\"ive Garc\'ia M\"{u}ller Fran\c{c}ois Pe\~na'
    assert normalize_tex_text_accents(source) == "naïve García Müller François Peña"


def test_chapter_normalization_applies_shared_text_accents() -> None:
    source = r'A na\"ive approach and M\"{u}ller\'s method.'
    assert normalize_latex(source) == "A naïve approach and Müller's method."


def test_author_conversion_reuses_shared_text_accents() -> None:
    source = r'Garc\'ia M\"{u}ller'
    assert latex_to_text(source) == "García Müller"


def test_math_accent_commands_are_untouched() -> None:
    source = r"$\tilde{x} + \hat{y} + \bar{z}$"
    assert normalize_tex_text_accents(source) == source


def test_unknown_accent_combination_is_preserved() -> None:
    source = r"\c{x}"
    assert normalize_tex_text_accents(source) == source
