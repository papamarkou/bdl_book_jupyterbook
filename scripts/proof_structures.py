#!/usr/bin/env python3
"""Reusable conversion of theorem-like TeX environments to native MyST proofs."""

from __future__ import annotations

import re

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


def _clean_title(text: str) -> str:
    """Convert conservative inline TeX used in theorem titles to MyST Markdown."""
    text = normalize_notation(text)
    text = re.sub(
        r"\\(?:cite|citep)\{([^{}]+)\}",
        lambda match: "[" + "; ".join(f"@{key.strip()}" for key in match.group(1).split(",")) + "]",
        text,
    )
    text = re.sub(
        r"\\citet\{([^{}]+)\}",
        lambda match: (
            f"@{match.group(1).strip()}"
            if "," not in match.group(1)
            else "[" + "; ".join(f"@{key.strip()}" for key in match.group(1).split(",")) + "]"
        ),
        text,
    )
    text = re.sub(r"\\(?:emph|textit)\{([^{}]*)\}", r"*\1*", text)
    text = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", text)
    text = text.replace("~", " ")
    return re.sub(r"\s+", " ", text).strip()


def mark_proof_environments(text: str) -> str:
    """Mark theorem-like boundaries before MyST's standalone LaTeX conversion.

    Optional theorem titles are retained explicitly so they can become native
    proof-directive titles after the LaTeX pass.
    """
    for kind in PROOF_KINDS:
        pattern = re.compile(
            rf"\\begin\{{{kind}\}}(?:\[([^\]]*)\])?(.*?)\\end\{{{kind}\}}",
            re.DOTALL,
        )

        def replace(match: re.Match[str], proof_kind: str = kind) -> str:
            title = match.group(1) or ""
            body = match.group(2)
            label_match = re.match(r"\s*\\label\{([^{}]+)\}\s*", body)
            label = label_match.group(1) if label_match else ""
            if label_match:
                body = body[label_match.end() :]

            lines = [f"BDLPROOFBEGIN {proof_kind}"]
            if label:
                lines.append(f"BDLPROOFLABEL {label}")
            if title:
                lines.append(f"BDLPROOFTITLE {_clean_title(title)}")
            lines.extend(["BDLPROOFBODY", body.strip(), f"BDLPROOFEND {proof_kind}"])
            return "\n\n" + "\n".join(lines) + "\n\n"

        text = pattern.sub(replace, text)
    return text


def restore_proof_directives(text: str) -> str:
    """Turn semantic proof markers into MyST's native proof directives."""
    pattern = re.compile(
        r"BDLPROOFBEGIN[ \t]+(example|proposition|definition|lemma|theorem|remark|assumption|proof)\s*\n"
        r"(?:BDLPROOFLABEL[ \t]+([^\n]+)\s*\n)?"
        r"(?:BDLPROOFTITLE[ \t]+([^\n]+)\s*\n)?"
        r"BDLPROOFBODY\s*\n(.*?)\n\s*BDLPROOFEND[ \t]+\1",
        flags=re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        kind = match.group(1)
        label = match.group(2).strip() if match.group(2) else None
        title = match.group(3).strip() if match.group(3) else None
        body = match.group(4).strip()

        if kind == "proof":
            lines = [":::{prf:proof}", ":enumerated: false"]
        else:
            heading = f":::{'{'}prf:{kind}{'}'}"
            if title:
                heading += f" {title}"
            lines = [heading]
        if label:
            lines.append(f":label: {label}")
        lines.extend(["", body, ":::"])
        return "\n".join(lines)

    previous = None
    while previous != text:
        previous = text
        text = pattern.sub(replace, text)
    return text
