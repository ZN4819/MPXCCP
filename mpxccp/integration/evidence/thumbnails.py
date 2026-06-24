from __future__ import annotations

from pathlib import Path


class ThumbnailGenerator:
    def create_thumbnail(
        self,
        source: Path,
        *,
        max_size: tuple[int, int] = (120, 80),
    ) -> Path | None:
        try:
            from PIL import Image
        except ImportError:
            return None

        try:
            thumbnail_dir = source.parent / ".thumbnails"
            thumbnail_dir.mkdir(exist_ok=True)
            thumbnail_path = thumbnail_dir / f"{source.stem}.png"
            with Image.open(source) as image:
                image.thumbnail(max_size)
                image.save(thumbnail_path, format="PNG")
            return thumbnail_path
        except Exception:
            return None