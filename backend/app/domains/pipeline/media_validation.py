"""Small standard-library raster inspection for packaged pipeline photographs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

APPLICATION_ROOT = Path(__file__).resolve().parents[4]
PIPELINE_MEDIA_ROOTS = (
    APPLICATION_ROOT / "frontend" / "public",
    APPLICATION_ROOT / "frontend" / "dist",
)


def resolve_pipeline_media_path(
    local_path: str,
    domain: str,
    *,
    media_roots: Sequence[Path] | None = None,
) -> Path:
    """Resolve an isolated pipeline asset from source or built runtime layout."""
    parsed = PurePosixPath(local_path)
    parts = parsed.parts
    filename = parts[-1] if parts else ""
    if (
        domain not in {"plants", "discoveries"}
        or parsed.as_posix() != local_path
        or len(parts) != 4
        or parts[:3] != ("/", "media", domain)
        or not filename.startswith("pipeline-")
        or Path(filename).suffix.casefold() not in {".jpg", ".jpeg", ".png"}
    ):
        raise ValueError("pipeline media path is outside the approved directory")

    roots = PIPELINE_MEDIA_ROOTS if media_roots is None else tuple(media_roots)
    relative = Path(*parts[1:])
    for root in roots:
        resolved_root = root.resolve()
        candidate = (resolved_root / relative).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError(
                "pipeline media path is outside the approved directory"
            ) from error
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(local_path)


@dataclass(frozen=True)
class RasterInfo:
    mime_type: str
    width: int
    height: int


def inspect_raster(path: Path) -> RasterInfo:
    """Read JPEG or PNG dimensions from file bytes; reject other/malformed files."""
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return RasterInfo("image/png", width, height)
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"{path.name}: file is not a supported photographic raster")
    position = 2
    while position + 9 < len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        marker = data[position + 1]
        position += 2
        if marker in {0xD8, 0xD9}:
            continue
        if position + 2 > len(data):
            break
        length = int.from_bytes(data[position : position + 2], "big")
        if length < 2 or position + length > len(data):
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            if width <= 0 or height <= 0:
                break
            return RasterInfo("image/jpeg", width, height)
        position += length
    raise ValueError(f"{path.name}: malformed JPEG dimensions")
