"""Batch file processor with filtering and transformation pipeline."""
from __future__ import annotations

import pathlib
from typing import Callable, Iterator


Transform = Callable[[str], str]
_ENCODING = "utf-8"


def read_lines(path: pathlib.Path) -> list[str]:
    """Read a text file and return its lines, stripping trailing newlines."""
    return path.read_text(encoding=_ENCODING).splitlines()


def write_lines(path: pathlib.Path, lines: list[str]) -> int:
    """Write lines to path (LF-terminated). Returns byte count written."""
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding=_ENCODING)
    return len(content.encode(_ENCODING))


class FileProcessor:
    """Apply a chain of transforms to every file matched by a glob pattern."""

    def __init__(self, transforms: list[Transform] | None = None) -> None:
        # transforms are applied left-to-right on file content
        self._transforms: list[Transform] = transforms or []

    def add_transform(self, transform: Transform) -> None:
        """Append a transform function to the pipeline."""
        self._transforms.append(transform)

    def process(self, path: pathlib.Path) -> str:
        """Read path, run all transforms, write result back. Returns new content."""
        content = path.read_text(encoding=_ENCODING)
        for transform in self._transforms:
            content = transform(content)
        path.write_text(content, encoding=_ENCODING)
        return content

    def process_glob(self, directory: pathlib.Path, pattern: str) -> Iterator[pathlib.Path]:
        """Process all files matching pattern under directory. Yields each processed path."""
        for path in sorted(directory.glob(pattern)):
            if path.is_file():
                self.process(path)
                yield path
