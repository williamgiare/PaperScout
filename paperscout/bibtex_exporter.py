"""BibTeX persistence helpers for PaperScout."""

from __future__ import annotations

from pathlib import Path

from .model import OutputConfig


class BibtexExporter:
    """Save BibTeX content to disk with conservative safety checks."""

    def save(self, content: str, output_config: OutputConfig) -> Path:
        if not content.strip():
            raise ValueError("Cannot save empty BibTeX content.")

        destination = output_config.destination
        parent_directory = destination.parent

        if output_config.create_parent_directories:
            parent_directory.mkdir(parents=True, exist_ok=True)
        elif not parent_directory.exists():
            raise FileNotFoundError(
                f"Parent directory does not exist: {parent_directory}"
            )

        if destination.exists() and not output_config.overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing file: {destination}"
            )

        destination.write_text(content.rstrip() + "\n", encoding="utf-8")
        return destination
