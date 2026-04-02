import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# Match ![[filename]] in markdown source (before rendering)
OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]]+?)\]\]")
# Match standard markdown images ![alt](path)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}


@dataclass
class AssetRef:
    original_ref: str
    source_path: Path | None  # None if not found
    output_filename: str


def _is_image(filename: str) -> bool:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in IMAGE_EXTENSIONS


def _find_file(filename: str, source_dir: Path) -> Path | None:
    """Find a file: try exact relative path first, then flat search by basename."""
    # Try exact relative path first
    exact = source_dir / filename
    if exact.is_file():
        return exact
    # Fall back to Obsidian-style flat matching (search by basename anywhere)
    basename = Path(filename).name
    matches = list(source_dir.rglob(basename))
    if matches:
        return matches[0]
    return None


def _content_hash(path: Path) -> str:
    """Return first 8 chars of the file's SHA-256 hash."""
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:8]


def collect_assets(articles: list, source_dir: Path, site=None) -> list[AssetRef]:
    """Scan articles for image references and resolve them against the source directory.

    If site.avatar is configured, it is also added as an asset to be copied.
    """
    seen: dict[str, AssetRef] = {}  # original_ref -> AssetRef

    for article in articles:
        # Obsidian embeds from raw markdown
        for match in OBSIDIAN_EMBED_RE.finditer(article.body_markdown):
            ref = match.group(1).strip()
            if not _is_image(ref) or ref in seen:
                continue
            source = _find_file(ref, source_dir)
            seen[ref] = AssetRef(
                original_ref=ref,
                source_path=source,
                output_filename=Path(ref).name,
            )

        # Standard markdown images from raw markdown
        for match in MD_IMAGE_RE.finditer(article.body_markdown):
            ref = match.group(1).strip()
            if ref.startswith("http://") or ref.startswith("https://"):
                continue  # skip external URLs
            if not _is_image(ref) or ref in seen:
                continue
            source = _find_file(ref, source_dir)
            seen[ref] = AssetRef(
                original_ref=ref,
                source_path=source,
                output_filename=Path(ref).name,
            )

    # Add site avatar if configured
    if site and site.avatar and site.avatar not in seen:
        avatar_source = _find_file(site.avatar, source_dir)
        seen[site.avatar] = AssetRef(
            original_ref=site.avatar,
            source_path=avatar_source,
            output_filename=Path(site.avatar).name,
        )

    # Handle filename collisions
    refs = list(seen.values())
    filename_groups: dict[str, list[AssetRef]] = {}
    for ref in refs:
        filename_groups.setdefault(ref.output_filename, []).append(ref)

    for filename, group in filename_groups.items():
        if len(group) > 1:
            for ref in group:
                if ref.source_path:
                    stem = Path(filename).stem
                    ext = Path(filename).suffix
                    ref.output_filename = f"{_content_hash(ref.source_path)}_{stem}{ext}"

    return refs


def copy_assets(asset_refs: list[AssetRef], output_dir: Path) -> list[str]:
    """Copy resolved assets to output/assets/. Returns list of warnings for missing files."""
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    for ref in asset_refs:
        if ref.source_path is None:
            warnings.append(f"Asset not found: {ref.original_ref}")
            continue
        dest = assets_dir / ref.output_filename
        shutil.copy2(ref.source_path, dest)

    return warnings
