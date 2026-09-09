#!/usr/bin/env python3
"""Convert Chapter 4 (Sequential Monte Carlo samplers) from LaTeX to native MyST Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path

from chapter_conversion import ChapterConfig, convert_chapter
from common import tex_path


CHAPTER_TITLE = "Sequential Monte Carlo samplers"
CHAPTER_LABEL = "chap:smcs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=tex_path("sampling_methods", "multilevel_smc", "main.tex"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("content/sampling_methods/multilevel_smc.md"),
        help="Chapter 4 output used by the normal book TOC.",
    )
    args = parser.parse_args()

    convert_chapter(
        ChapterConfig(
            title=CHAPTER_TITLE,
            label=CHAPTER_LABEL,
            input_path=args.input,
            output_path=args.output,
            asset_slug="multilevel_smc",
        )
    )


if __name__ == "__main__":
    main()
