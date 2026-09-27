#!/usr/bin/env python3
"""Télécharge les nouvelles vidéos d'une playlist YouTube en MP3 avec pochette."""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import yt_dlp
from yt_dlp.utils import sanitize_filename

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list=PL8FdYgsyVXS37c1Yc1RPPsytBjPhca1jw"
)
DOWNLOAD_DIR = Path(r"C:\Users\brune\Desktop\Musique\Download\Boumboum")
ARCHIVE_FILE = DOWNLOAD_DIR / "archive.txt"
BASELINE_FILE = DOWNLOAD_DIR / ".baseline_done"
BASELINE_IDS_FILE = DOWNLOAD_DIR / "baseline_ids.txt"
AUDIO_QUALITY = "320"
THUMB_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}


def check_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg est introuvable dans le PATH. Installez-le puis relancez le script."
        )

    try:
        import mutagen  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Le module mutagen est requis pour intégrer la pochette dans les MP3."
        ) from exc


def build_ydl_opts(*, match_filter=None) -> dict:
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "download_archive": str(ARCHIVE_FILE),
        "ignoreerrors": True,
        "noplaylist": True,
        "writethumbnail": True,
        "keepvideo": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": AUDIO_QUALITY,
            },
            {"key": "FFmpegMetadata"},
            {
                "key": "FFmpegThumbnailsConvertor",
                "format": "jpg",
            },
            {"key": "EmbedThumbnail"},
        ],
        "postprocessor_args": {
            "EmbedThumbnail": ["-c:v", "mjpeg"],
        },
        "quiet": False,
        "no_warnings": False,
    }
    if match_filter is not None:
        opts["match_filter"] = match_filter
    return opts


def fetch_playlist_entries() -> list[dict]:
    ydl_opts: dict = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(PLAYLIST_URL, download=False)

    entries = info.get("entries") or []
    return [entry for entry in entries if entry and entry.get("id")]


def fetch_playlist_ids() -> set[str]:
    return {entry["id"] for entry in fetch_playlist_entries()}


def title_to_stem(title: str) -> str:
    return sanitize_filename(title, restricted=True)


def load_id_file(path: Path) -> set[str]:
    if not path.exists():
        return set()

    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("youtube "):
            parts = line.split()
            if len(parts) >= 2:
                ids.add(parts[1])
        else:
            ids.add(line)
    return ids


def save_id_file(path: Path, ids: set[str]) -> None:
    if path == ARCHIVE_FILE:
        lines = [f"youtube {video_id}" for video_id in sorted(ids)]
    else:
        lines = sorted(ids)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def remove_ids_from_archive(video_ids: set[str]) -> None:
    if not video_ids or not ARCHIVE_FILE.exists():
        return

    remaining: list[str] = []
    for line in ARCHIVE_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] in video_ids:
            continue
        if line.strip():
            remaining.append(line.strip())

    ARCHIVE_FILE.write_text(
        "\n".join(remaining) + ("\n" if remaining else ""),
        encoding="utf-8",
    )


def save_baseline_ids(video_ids: set[str]) -> None:
    save_id_file(BASELINE_IDS_FILE, video_ids)


def migrate_legacy_baseline() -> None:
    """Compatibilite avec l'ancienne version qui remplissait archive.txt au baseline."""
    if BASELINE_IDS_FILE.exists() or not BASELINE_FILE.exists():
        return

    legacy_ids = load_id_file(ARCHIVE_FILE)
    if legacy_ids:
        save_baseline_ids(legacy_ids)
        print(
            f"Migration : {len(legacy_ids)} ID(s) deja presents "
            "deplaces vers baseline_ids.txt."
        )


def load_baseline_ids() -> set[str]:
    return load_id_file(BASELINE_IDS_FILE)


def load_archive_ids() -> set[str]:
    return load_id_file(ARCHIVE_FILE)


def find_orphan_thumbnails() -> list[Path]:
    orphans: list[Path] = []
    if not DOWNLOAD_DIR.exists():
        return orphans

    for path in DOWNLOAD_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in THUMB_EXTENSIONS:
            continue
        if not path.with_suffix(".mp3").exists():
            orphans.append(path)
    return sorted(orphans)


def map_stem_to_video_id(entries: list[dict]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in entries:
        title = entry.get("title") or ""
        video_id = entry.get("id")
        if not video_id:
            continue
        mapping[title_to_stem(title)] = video_id
    return mapping


def map_stem_to_video_id_fuzzy(
    stem: str, mapping: dict[str, str]
) -> str | None:
    if stem in mapping:
        return mapping[stem]

    stem_lower = stem.lower()
    for key, video_id in mapping.items():
        if key.lower() == stem_lower:
            return video_id

    for key, video_id in mapping.items():
        if stem_lower in key.lower() or key.lower() in stem_lower:
            return video_id

    return None


def resolve_orphan_video_ids(
    orphans: list[Path], entries: list[dict]
) -> tuple[set[str], list[str]]:
    stem_map = map_stem_to_video_id(entries)
    video_ids: set[str] = set()
    unresolved: list[str] = []

    for thumb in orphans:
        video_id = map_stem_to_video_id_fuzzy(thumb.stem, stem_map)
        if video_id:
            video_ids.add(video_id)
        else:
            unresolved.append(thumb.name)

    return video_ids, unresolved


def cleanup_orphan_thumbnails() -> int:
    removed = 0
    for thumb in find_orphan_thumbnails():
        mp3 = thumb.with_suffix(".mp3")
        if mp3.exists():
            continue
        try:
            thumb.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def download_video_urls(urls: list[str], *, label: str) -> int:
    if not urls:
        return 0

    print(f"\n{label} : {len(urls)} video(s)")
    ydl_opts = build_ydl_opts()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        errors = ydl.download(urls)

    if errors:
        print(f"Termine avec {errors} erreur(s) pour {label}.")
    return errors or 0


def repair_incomplete_downloads() -> int:
    orphans = find_orphan_thumbnails()
    if not orphans:
        return 0

    print(f"Reparation : {len(orphans)} pochette(s) sans MP3 detectee(s).")
    entries = fetch_playlist_entries()
    video_ids, unresolved = resolve_orphan_video_ids(orphans, entries)

    if unresolved:
        print("Fichiers non associes a une video de la playlist :")
        for name in unresolved[:10]:
            print(f"  - {name}")
        if len(unresolved) > 10:
            print(f"  ... et {len(unresolved) - 10} autre(s)")

    if not video_ids:
        print("Impossible de retrouver les videos correspondantes.")
        return 0

    remove_ids_from_archive(video_ids)
    urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in sorted(video_ids)]
    return download_video_urls(urls, label="Retelechargement MP3 manquants")


def count_pending_downloads() -> tuple[int, set[str]]:
    playlist_ids = fetch_playlist_ids()
    baseline_ids = load_baseline_ids()
    archive_ids = load_archive_ids()
    pending = playlist_ids - baseline_ids - archive_ids
    return len(pending), pending


def ensure_baseline() -> None:
    migrate_legacy_baseline()

    if BASELINE_FILE.exists():
        return

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print("Initialisation : marquage des vidéos déjà présentes dans la playlist...")
    playlist_ids = fetch_playlist_ids()
    save_baseline_ids(playlist_ids)
    BASELINE_FILE.write_text(
        f"{len(playlist_ids)} vidéos ignorées à partir du {date.today()}\n",
        encoding="utf-8",
    )
    print(
        f"{len(playlist_ids)} video(s) enregistree(s) dans baseline_ids.txt "
        f"({len(playlist_ids)} au total dans la playlist)."
    )
    print("Seules les vidéos ajoutées désormais seront téléchargées.\n")


def download_playlist() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    repair_errors = repair_incomplete_downloads()

    baseline_ids = load_baseline_ids()

    def match_filter(info: dict, *, incomplete: bool) -> str | None:
        video_id = info.get("id")
        if video_id and video_id in baseline_ids:
            return None
        return info.get("title") or "video"

    pending_count, pending_ids = count_pending_downloads()
    print(f"Nouvelles vidéos à télécharger : {pending_count}")

    if pending_count == 0 and repair_errors == 0:
        print("Aucune nouvelle vidéo détectée. Synchronisation terminée.")
        return

    if pending_count == 0:
        print("Synchronisation terminée (reparation effectuee).")
        return

    ydl_opts = build_ydl_opts(match_filter=match_filter)
    ydl_opts["noplaylist"] = False

    print(f"Playlist : {PLAYLIST_URL}")
    print(f"Dossier  : {DOWNLOAD_DIR}")
    print(f"Archive  : {ARCHIVE_FILE}")
    print(f"Qualité  : MP3 {AUDIO_QUALITY} kbps")
    if pending_ids:
        print(f"IDs     : {', '.join(sorted(pending_ids)[:5])}"
              + (" ..." if len(pending_ids) > 5 else ""))
    print()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        errors = ydl.download([PLAYLIST_URL])

    if errors:
        print(f"\nTerminé avec {errors} erreur(s).")
    else:
        print("\nSynchronisation terminée.")

    still_orphans = find_orphan_thumbnails()
    if still_orphans:
        print(
            f"\nAttention : {len(still_orphans)} pochette(s) sans MP3 "
            "restent. Relancez le script ou verifiez FFmpeg / la connexion."
        )


def main() -> int:
    try:
        check_dependencies()
        ensure_baseline()
        download_playlist()
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
