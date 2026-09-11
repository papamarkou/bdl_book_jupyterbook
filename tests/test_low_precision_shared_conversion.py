from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from latex_normalize import normalize_latex, normalize_notation  # noqa: E402
from myst_structures import algorithm_to_myst, extract_figures  # noqa: E402


def test_low_precision_math_macros_are_expanded() -> None:
    source = r"\rd t, \norm{\theta-\theta'}_2, \Var_v^{hmc}"
    converted = normalize_notation(source)

    assert r"\,\mathrm{d} t" in converted
    assert r"\left\lVert \theta-\theta' \right\rVert_2" in converted
    assert r"\mathbb{V}_v^{hmc}" in converted
    assert r"\rd" not in converted
    assert r"\norm" not in converted
    assert r"\Var" not in converted


def test_legacy_it_declaration_is_normalized_without_touching_item() -> None:
    source = r"{\it dissipative} \paragraph{\it Sampling Thinning} \item value"
    converted = normalize_latex(source)

    assert r"\textit{dissipative}" in converted
    assert r"\paragraph{\textit{Sampling Thinning}}" in converted
    assert r"\item value" in converted
    assert r"{\it" not in converted


def test_algorithm2e_foreach_else_and_kwret_are_converted() -> None:
    source = r"""
\caption{Variance-corrected quantization}
\label{alg:vc}
\ForEach{$i$}{
  \If{$v > v_s$}{
    $x \gets 1$\;
  }
  \Else{
    $x \gets 0$\;
  }
}
\KwRet{$x$}
"""
    converted = algorithm_to_myst(source)

    assert "**For each** {math}`i`:" in converted
    assert "**If** {math}`v > v_s`:" in converted
    assert "**Else:**" in converted
    assert "**Return** {math}`x`" in converted
    assert r"\ForEach" not in converted
    assert r"\Else" not in converted
    assert r"\KwRet" not in converted


def test_starred_multi_image_figure_is_extracted() -> None:
    source = r"""
\begin{figure*}
\centering
\includegraphics[width=4cm]{sampling_methods/example/fig/a.pdf}
\includegraphics[width=4cm]{sampling_methods/example/fig/b.pdf}
\caption{Two panels.}
\label{fig:star}
\end{figure*}
"""
    marked, structures = extract_figures(source)

    assert marked.strip() == "BDLFIGUREPLACEHOLDER0000"
    assert len(structures) == 1
    markdown = structures[0].markdown
    assert "sampling_methods/example/fig/a.pdf" in markdown
    assert "sampling_methods/example/fig/b.pdf" in markdown
    assert ":label: fig:star" in markdown
    assert "Two panels." in markdown
