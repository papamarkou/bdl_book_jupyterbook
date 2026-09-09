#!/usr/bin/env python3
"""Reusable conversion of theorem-like TeX environments to native MyST proofs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from latex_normalize import normalize_notation


PROOF_KINDS = (
    "example",
    "proposition",
    "definition",
    "lemma",
    "theorem",
    "remark",
    "assumption",
    "proof",
)


@dataclass(frozen=True)
class ProofStructure:
    """Metadata protected while MyST converts a theorem-like environment body."""

    begin_token: str
    end_token: str
    kind: str
    label: str | None
    title: str | None


def _clean_title(text: str) -> str:
    """Convert conservative inline TeX used in theorem titles to MyST Markdown."""
    text = normalize_notation(text)
    text = re.sub(
        r"\\(?:cite|citep)\{([^{}]+)\}",
        lambda match: "[" + "; ".join(
            f"@{key.strip()}" for key in match.group(1).split(",") if key.strip()
        ) + "]",
        text,
    )
    text = re.sub(
        r"\\citet\{([^{}]+)\}",
        lambda match: (
            f"@{match.group(1).strip()}"
            if "," not in match.group(1)
            else "[" + "; ".join(
                f"@{key.strip()}" for key in match.group(1).split(",") if key.strip()
            ) + "]"
        ),
        text,
    )
    text = re.sub(r"\\(?:emph|textit)\{([^{}]*)\}", r"*\1*", text)
    text = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", text)
    text = text.replace("~", " ")
    return re.sub(r"\s+", " ", text).strip()


def mark_proof_environments(text: str) -> tuple[str, list[ProofStructure]]:
    """Protect theorem boundaries while leaving their bodies for MyST conversion.

    Only opaque begin/end tokens are passed through MyST. Semantic metadata is
    retained separately in ``ProofStructure`` objects, so MyST cannot reflow or
    expose it in generated Markdown.
    """
    structures: list[ProofStructure] = []

    for kind in PROOF_KINDS:
        pattern = re.compile(
            rf"\\begin\{{{kind}\}}(?:\[([^\]]*)\])?(.*?)\\end\{{{kind}\}}",
            re.DOTALL,
        )

        def replace(match: re.Match[str], proof_kind: str = kind) -> str:
            title = _clean_title(match.group(1)) if match.group(1) else None
            body = match.group(2)
            label_match = re.match(r"\s*\\label\{([^{}]+)\}\s*", body)
            label = label_match.group(1) if label_match else None
            if label_match:
                body = body[label_match.end() :]

            index = len(structures)
            begin_token = f"BDLPROOFBEGINPLACEHOLDER{index:04d}"
            end_token = f"BDLPROOFENDPLACEHOLDER{index:04d}"
            structures.append(
                ProofStructure(
                    begin_token=begin_token,
                    end_token=end_token,
                    kind=proof_kind,
                    label=label,
                    title=title,
                )
            )
            return f"\n\n{begin_token}\n\n{body.strip()}\n\n{end_token}\n\n"

        text = pattern.sub(replace, text)

    return text, structures


def _directive(structure: ProofStructure, body: str) -> str:
    """Build one native MyST proof directive from protected metadata and body."""
    if structure.kind == "proof":
        lines = [":::{prf:proof}", ":enumerated: false"]
    else:
        heading = f":::{{prf:{structure.kind}}}"
        if structure.title:
            heading += f" {structure.title}"
        lines = [heading]

    if structure.label:
        lines.append(f":label: {structure.label}")
    lines.extend(["", body.strip(), ":::"])
    return "\n".join(lines)


def restore_proof_directives(text: str, structures: list[ProofStructure]) -> str:
    """Restore protected theorem-like regions as native MyST proof directives."""
    for structure in structures:
        start = text.find(structure.begin_token)
        end = text.find(structure.end_token, start + len(structure.begin_token))
        if start < 0 or end < 0:
            raise ValueError(
                "Could not restore proof structure: "
                f"{structure.kind} label={structure.label!r}"
            )

        body_start = start + len(structure.begin_token)
        body = text[body_start:end]
        replacement = _directive(structure, body)
        text = text[:start] + replacement + text[end + len(structure.end_token) :]

    if "BDLPROOF" in text:
        raise ValueError("Unrestored BDL proof placeholder remained in generated Markdown")
    return text
