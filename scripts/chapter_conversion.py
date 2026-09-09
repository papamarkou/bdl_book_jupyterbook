#!/usr/bin/env python3
"""Reusable driver for converting one TeX chapter to native MyST Markdown."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from common import TEX_ROOT
from footnote_structures import FootnoteStructure, extract_footnotes, restore_footnotes
from latex_normalize import (
    normalize_latex,
    normalize_pre_extraction,
    normalize_typography,
    strip_tex_comments,
)
from myst_structures import (
    ExtractedStructure,
    extract_algorithms,
    extract_figures,
    normalize_headings_for_latex_pass,
)
from proof_structures import ProofStructure, extract_proof_environments, proof_directive
from semantic_references import extract_references


MYST_TIMEOUT_SECONDS = 60
WEB_IMAGE_EXTENSIONS = (".svg", ".png", ".webp", ".jpg", ".jpeg")


@dataclass(frozen=True)
class ChapterConfig:
    """Chapter-specific inputs for the shared conversion pipeline."""

    title: str
    label: str
    input_path: Path
    output_path: Path
    asset_slug: str


def prepare_latex(
    text: str,
) -> tuple[
    str,
    list[ExtractedStructure],
    list[ProofStructure],
    list[FootnoteStructure],
]:
    """Apply shared structural extraction and LaTeX normalization."""
    text = normalize_pre_extraction(text)
    text = strip_tex_comments(text)
    text = normalize_typography(text)

    text, footnote_structures = extract_footnotes(text)
    text, structures = extract_algorithms(text)

    text, figure_structures = extract_figures(text)
    structures.extend(figure_structures)

    text, reference_structures = extract_references(text)
    structures.extend(reference_structures)

    text, proof_structures = extract_proof_environments(text)

    text = normalize_latex(text)
    text = normalize_headings_for_latex_pass(text)
    return text, structures, proof_structures, footnote_structures


def _strip_export_frontmatter(text: str) -> str:
    """Remove YAML added by MyST's standalone Markdown export."""
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)


def summarize_myst_output(output: str) -> None:
    """Print one compact aggregate summary of MyST diagnostics for a chapter."""
    diagnostics = [
        line.strip() for line in output.splitlines() if "Unhandled TEX conversion" in line
    ]
    if not diagnostics:
        print("MyST reported no unhandled TeX nodes in the normalized chapter.")
        return

    kinds: Counter[str] = Counter()
    for line in diagnostics:
        match = re.search(r'node of "([^"]+)"', line)
        kinds[match.group(1) if match else "unknown"] += 1

    summary = ", ".join(f"{kind}: {count}" for kind, count in kinds.most_common())
    print(f"MyST reported {len(diagnostics)} unhandled TeX nodes ({summary}).")


def run_myst_isolated(normalized: str) -> tuple[str, str]:
    """Convert only the normalized TeX file in an isolated temporary directory."""
    with tempfile.TemporaryDirectory(prefix="bdl-myst-") as temp_dir_name:
        work_dir = Path(temp_dir_name)
        tex_file = work_dir / "chapter.tex"
        tex_file.write_text(normalized, encoding="utf-8")

        for child in TEX_ROOT.iterdir():
            if child.is_dir():
                (work_dir / child.name).symlink_to(child.resolve())

        log_path = work_dir / "myst.log"
        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                result = subprocess.run(
                    ["myst", "build", tex_file.name, "--md"],
                    cwd=work_dir,
                    check=False,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=MYST_TIMEOUT_SECONDS,
                )
        except subprocess.TimeoutExpired as exc:
            output = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
            tail = "\n".join(output.splitlines()[-20:])
            raise RuntimeError(
                f"MyST conversion exceeded {MYST_TIMEOUT_SECONDS} seconds. "
                f"Final diagnostics:\n{tail}"
            ) from exc

        output = log_path.read_text(encoding="utf-8")

        if result.returncode != 0:
            tail = "\n".join(output.splitlines()[-20:])
            raise RuntimeError(f"MyST conversion failed. Final diagnostics:\n{tail}")

        export_path = work_dir / "_build" / "exports" / "chapter.md"
        if not export_path.exists():
            raise FileNotFoundError(f"MyST did not create the expected Markdown export: {export_path}")

        return export_path.read_text(encoding="utf-8"), output


def _convert_fragment(tex: str, myst_outputs: list[str]) -> str:
    """Convert one non-empty normalized TeX fragment to Markdown."""
    if not tex.strip():
        return ""
    generated, output = run_myst_isolated(tex)
    myst_outputs.append(output)
    return _strip_export_frontmatter(generated).strip()


def run_myst_with_structures(
    normalized: str,
    structures: list[ExtractedStructure],
    proof_structures: list[ProofStructure],
) -> str:
    """Convert ordinary TeX fragments while resolving semantic structures in Python.

    Algorithms, figures, semantic references, and theorem-like environments are
    never passed through MyST as opaque placeholders. Their placeholders are used
    only as split points here, which avoids MyST dropping or rewriting them.
    """
    ordinary = {structure.placeholder: structure.markdown for structure in structures}
    proofs = {structure.placeholder: structure for structure in proof_structures}
    all_placeholders = list(ordinary) + list(proofs)
    myst_outputs: list[str] = []

    if not all_placeholders:
        converted = _convert_fragment(normalized, myst_outputs)
        summarize_myst_output("\n".join(myst_outputs))
        return converted

    pattern = re.compile(
        "(" + "|".join(re.escape(key) for key in sorted(all_placeholders, key=len, reverse=True)) + ")"
    )

    def convert_stream(tex: str) -> str:
        parts: list[str] = []
        for piece in pattern.split(tex):
            if not piece:
                continue

            if piece in ordinary:
                parts.append(ordinary[piece])
                continue

            proof = proofs.get(piece)
            if proof is not None:
                body = normalize_latex(proof.body_tex)
                body_markdown = convert_stream(body)
                parts.append(proof_directive(proof, body_markdown))
                continue

            converted = _convert_fragment(piece, myst_outputs)
            if converted:
                parts.append(converted)

        return "\n\n".join(part for part in parts if part.strip())

    converted = convert_stream(normalized)
    summarize_myst_output("\n".join(myst_outputs))

    for placeholder in all_placeholders:
        if placeholder in converted:
            raise ValueError(f"Unrestored semantic placeholder remained: {placeholder}")

    return converted


def clean_generated_markdown(
    text: str,
    footnote_structures: list[FootnoteStructure],
    *,
    title: str,
    label: str,
) -> str:
    """Restore footnotes and add one canonical chapter heading."""
    text = _strip_export_frontmatter(text)
    text = restore_footnotes(text, footnote_structures)

    # Extracted algorithm bodies can contain TeX's non-breaking-space marker
    # immediately before an already converted Markdown reference.
    text = re.sub(
        r"\b(Algorithm|Theorem|Proposition|Lemma|Definition|Remark|Assumption)~(?=\[\]\(#)",
        r"\1 ",
        text,
    )

    text = re.sub(
        rf"\A\s*\({re.escape(label)}\)=\s*\n",
        "",
        text,
        count=1,
    )
    text = re.sub(
        rf"\A\s*#+\s+{re.escape(title)}\s*\n",
        "",
        text,
        count=1,
    )

    text = re.sub(r"\n{3,}", "\n\n", text)
    if "BDLPROOFPLACEHOLDER" in text:
        raise ValueError("Unrestored proof placeholder remained in generated Markdown")
    if "BDLREFERENCEPLACEHOLDER" in text:
        raise ValueError("Unrestored reference placeholder remained in generated Markdown")
    if "BDLALGORITHMPLACEHOLDER" in text:
        raise ValueError("Unrestored algorithm placeholder remained in generated Markdown")
    if "BDLFIGUREPLACEHOLDER" in text:
        raise ValueError("Unrestored figure placeholder remained in generated Markdown")
    if "BDLFOOTNOTEPLACEHOLDER" in text:
        raise ValueError("Unrestored footnote placeholder remained in generated Markdown")
    return f"({label})=\n# {title}\n\n{text.lstrip()}"


def _source_image_prefix(source_dir: Path) -> str:
    """Return the TeX-root-relative figure prefix used in generated Markdown."""
    relative = source_dir.resolve().relative_to(TEX_ROOT.resolve())
    return f"{relative.as_posix()}/fig/"


def copy_and_rewrite_images(
    markdown: str,
    *,
    source_dir: Path,
    output_path: Path,
    asset_slug: str,
) -> str:
    """Copy chapter figures into the book and rewrite generated image paths."""
    source_fig_dir = source_dir / "fig"
    if not source_fig_dir.exists():
        return markdown

    target_fig_dir = output_path.parent / "assets" / asset_slug
    target_fig_dir.mkdir(parents=True, exist_ok=True)
    source_prefix = _source_image_prefix(source_dir)
    pattern = re.compile(re.escape(source_prefix) + r"([^\s)\]}]+)")

    def replace(match: re.Match[str]) -> str:
        requested_name = match.group(1)
        requested = source_fig_dir / requested_name
        chosen = requested

        if requested.suffix.lower() == ".pdf":
            for extension in WEB_IMAGE_EXTENSIONS:
                candidate = requested.with_suffix(extension)
                if candidate.exists():
                    chosen = candidate
                    break

        if not chosen.exists():
            return match.group(0)

        destination = target_fig_dir / chosen.name
        shutil.copy2(chosen, destination)
        return f"assets/{asset_slug}/{chosen.name}"

    return pattern.sub(replace, markdown)


def convert_chapter(config: ChapterConfig) -> None:
    """Run the complete shared TeX-to-MyST conversion pipeline for one chapter."""
    source = config.input_path.read_text(encoding="utf-8")
    normalized, structures, proof_structures, footnote_structures = prepare_latex(source)
    generated = run_myst_with_structures(normalized, structures, proof_structures)

    markdown = clean_generated_markdown(
        generated,
        footnote_structures,
        title=config.title,
        label=config.label,
    )
    markdown = copy_and_rewrite_images(
        markdown,
        source_dir=config.input_path.parent,
        output_path=config.output_path,
        asset_slug=config.asset_slug,
    )

    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {config.output_path}")
