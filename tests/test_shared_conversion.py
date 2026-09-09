from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from chapter_conversion import prepare_latex  # noqa: E402
from footnote_structures import extract_footnotes, restore_footnotes  # noqa: E402
from latex_normalize import normalize_latex, normalize_notation, normalize_pre_extraction  # noqa: E402
from myst_structures import algorithm_to_myst, figure_to_myst  # noqa: E402
from proof_structures import extract_proof_environments, proof_directive  # noqa: E402
from semantic_references import extract_references  # noqa: E402


def test_book_expectation_macro_is_expanded() -> None:
    source = r"\E[\theta\sim p(\theta)][p(y\mid x,\theta)]"
    converted = normalize_notation(source)
    assert r"\mathbb{E}_{\theta\sim p(\theta)}\left[p(y\mid x,\theta)\right]" == converted


def test_shared_gaussian_and_transpose_macros_are_expanded() -> None:
    source = r"\bm{r}\transpose \sim \N(\bm{0},\bm{I})"
    converted = normalize_notation(source)
    assert r"\bm{r}^{\top} \sim \mathcal{N}(\bm{0},\bm{I})" == converted


def test_chapter4_sampling_macros_are_expanded() -> None:
    source = r"\numPar, \idxPar, \sX"
    assert normalize_notation(source) == r"R, r, \mathsf{X}"


def test_roman_numerals_are_literal_text() -> None:
    assert normalize_notation(r"\romannumeral1) first; \romannumeral2) second") == (
        "i) first; ii) second"
    )


def test_kl_macro_supports_nested_braces() -> None:
    source = r"\KL{p(\theta\mid x)}{q_{\psi}(\theta\mid x)}"
    converted = normalize_notation(source)
    assert converted == (
        r"D_{KL}\left(p(\theta\mid x)\middle\|q_{\psi}(\theta\mid x)\right)"
    )
    assert r"\KL" not in converted


def test_capital_tilde_is_normalized() -> None:
    assert normalize_notation(r"\Tilde{w}_i") == r"\widetilde{w}_i"


def test_argmin_and_argmax_are_expanded() -> None:
    source = r"\argmin_{\psi} L(\psi), \argmax_{\theta} p(\theta)"
    converted = normalize_notation(source)
    assert r"\operatorname*{arg\,min}_{\psi}" in converted
    assert r"\operatorname*{arg\,max}_{\theta}" in converted


def test_nonsemantic_typography_is_normalized() -> None:
    source = r"\noindent{\bf Regression. } \textcolor{black}{Body} {\color{black} More}"
    converted = normalize_latex(source)
    assert converted == r"\textbf{Regression. } Body More"
    assert r"\noindent" not in converted
    assert r"\textcolor" not in converted
    assert r"\color" not in converted
    assert r"{\bf" not in converted


def test_abbreviated_semantic_references_are_normalized() -> None:
    source = r"""
\section{Sequential inference}
\label{sec:sequential}
See Eq.~\ref{eq:npe}, Sec.~\ref{sec:sequential}, and Fig.~\ref{fig:overview}.
"""
    converted, structures = extract_references(source)
    restored = converted
    for structure in structures:
        restored = restored.replace(structure.placeholder, structure.markdown)

    assert "Equation [](#eq:npe)" in restored
    assert "Section [Sequential inference](#sec:sequential)" in restored
    assert "Figure [](#fig:overview)" in restored
    assert r"Eq.~\ref" not in restored
    assert r"Sec.~\ref" not in restored
    assert r"Fig.~\ref" not in restored


def test_full_equation_word_preserves_lowercase() -> None:
    source = r"The algorithm satisfies the equation \eqref{eq:invariance}."
    converted, structures = extract_references(source)
    restored = converted
    for structure in structures:
        restored = restored.replace(structure.placeholder, structure.markdown)

    assert "satisfies the equation [](#eq:invariance)" in restored


def test_algorithm_and_theorem_references_are_semantic_links() -> None:
    source = (
        r"See Algorithm \ref{alg:smc} and Theorem \ref{thm:main}."
    )
    converted, structures = extract_references(source)
    restored = converted
    for structure in structures:
        restored = restored.replace(structure.placeholder, structure.markdown)

    assert "Algorithm [](#alg:smc)" in restored
    assert "Theorem [](#thm:main)" in restored
    assert "%s" not in restored
    assert r"\ref" not in restored


def test_algorithm2e_aligned_tcp_comment_is_preserved() -> None:
    source = r"""
\caption{Example}
\label{alg:example}
\SetKwInOut{Input}{Inputs}
\SetKwInOut{Output}{Outputs}
\Input{dataset $\mathcal{D}$}
$x \gets 1$ \tcp*[r]{Compute value}
"""
    converted = algorithm_to_myst(source)
    assert "**Inputs:**" in converted
    assert "*Note:* Compute value" in converted
    assert r"\tcp" not in converted


def test_algorithm2e_repeat_loop_is_converted_recursively() -> None:
    source = r"""
\caption{Repeat example}
\label{alg:repeat}
\Repeat{termination criterion met}{
  \tcp{Effective sample size}
  $n \gets n+1$\;
}
"""
    converted = algorithm_to_myst(source)
    assert "**Repeat until** termination criterion met:" in converted
    assert "*Note:* Effective sample size" in converted
    assert r"\Repeat" not in converted
    assert r"\tcp" not in converted


def test_algorithm_caption_supports_nested_tex_braces() -> None:
    source = r"""
\caption{Sequential Monte Carlo to estimate $\mathbb{E}(\theta_n)$}
\label{alg:smc}
$x \gets 1$\;
"""
    converted = algorithm_to_myst(source)
    assert converted.startswith(
        r":::{prf:algorithm} Sequential Monte Carlo to estimate $\mathbb{E}(\theta_n)$"
    )
    assert r"\caption" not in converted


def test_figure_width_accepts_linewidth() -> None:
    source = r"""
\centering
\includegraphics[width=0.8\linewidth]{sampling_methods/sg_mcmc/fig/example.pdf}
\caption{Example figure.}
\label{fig:example}
"""
    converted = figure_to_myst(source)
    assert ":width: 80%" in converted


def test_figure_width_accepts_columnwidth_through_shared_prepass() -> None:
    source = r"""
\centering
\includegraphics[width=0.45\columnwidth]{sampling_methods/example/fig/panel.png}
\caption{Example figure.}
\label{fig:columnwidth}
"""
    converted = figure_to_myst(normalize_pre_extraction(source))
    assert ":width: 45%" in converted


def test_citations_are_preserved_inside_extracted_caption() -> None:
    source = r"""
\centering
\includegraphics{sampling_methods/sg_mcmc/fig/example.pdf}
\caption{Adapted from \cite{smith2020} and discussed by \citet{jones2021}.}
\label{fig:example}
"""
    converted = figure_to_myst(source)
    assert "[@smith2020]" in converted
    assert "@jones2021" in converted
    assert r"\cite" not in converted


def test_theorem_optional_title_and_citation_are_preserved() -> None:
    source = r"""
\begin{theorem}[Giles \citep{giles2008multilevel}]
\label{thm:VMLMC}
The estimator achieves the stated complexity.
\end{theorem}
"""
    marked, structures = extract_proof_environments(source)
    assert marked.strip() == "BDLPROOFPLACEHOLDER0000"
    assert len(structures) == 1
    structure = structures[0]
    assert structure.kind == "theorem"
    assert structure.label == "thm:VMLMC"
    assert structure.title == "Giles [@giles2008multilevel]"
    assert structure.body_tex == "The estimator achieves the stated complexity."

    restored = proof_directive(structure, structure.body_tex)
    assert restored.startswith(":::{prf:theorem} Giles [@giles2008multilevel]")
    assert ":label: thm:VMLMC" in restored
    assert "The estimator achieves the stated complexity." in restored


def test_commented_proof_environments_are_ignored_before_extraction() -> None:
    source = r"""
% \begin{proposition}
% \label{prop:commented}
% This must not become a proof structure.
% \end{proposition}

\begin{proposition}
\label{prop:active}
This one is active.
\end{proposition}
"""
    normalized, structures, proof_structures, footnote_structures = prepare_latex(source)

    assert len(proof_structures) == 1
    assert proof_structures[0].label == "prop:active"
    assert proof_structures[0].placeholder == "BDLPROOFPLACEHOLDER0000"
    assert "prop:commented" not in normalized
    assert all("prop:commented" not in structure.markdown for structure in structures)
    assert not footnote_structures


def test_footnotes_are_deterministic_and_not_duplicated() -> None:
    source = (
        r"Approximate posteriors can be overconfident"
        r"\footnote{This occurs when the approximation is too narrow.}, particularly."
    )
    marked, structures = extract_footnotes(source)
    assert marked == (
        "Approximate posteriors can be overconfident"
        "BDLFOOTNOTEPLACEHOLDER0001, particularly."
    )
    assert len(structures) == 1
    assert structures[0].identifier == "footnote-1"

    restored = restore_footnotes(marked, structures)
    assert restored.count("[^footnote-1]") == 2
    assert (
        "Approximate posteriors can be overconfident[^footnote-1], particularly."
        in restored
    )
    assert (
        "[^footnote-1]: This occurs when the approximation is too narrow."
        in restored
    )
    assert "BDLFOOTNOTEPLACEHOLDER" not in restored
