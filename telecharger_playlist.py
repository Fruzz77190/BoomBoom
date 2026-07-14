#!/usr/bin/env python3
"""Télécharge les nouvelles vidéos d'une playlist YouTube en MP3 avec pochette."""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import yt_dlp

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list=PL8FdYgsyVXS37c1Yc1RPPsytBjPhca1jw"
)
DOWNLOAD_DIR = Path(r"C:\Users\brune\Desktop\Musique\Download\Boumboum")
ARCHIVE_FILE = DOWNLOAD_DIR / "archive.txt"
BASELINE_FILE = DOWNLOAD_DIR / ".baseline_done"
BASELINE_IDS_FILE = DOWNLOAD_DIR / "baseline_ids.txt"
AUDIO_QUALITY = "320"


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


def fetch_playlist_ids() -> set[str]:
    ydl_opts: dict = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(PLAYLIST_URL, download=False)

    entries = info.get("entries") or []
    return {
        entry["id"]
        for entry in entries
        if entry and entry.get("id")
    }


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


def save_baseline_ids(video_ids: set[str]) -> None:
    BASELINE_IDS_FILE.write_text(
        "\n".join(sorted(video_ids)) + "\n",
        encoding="utf-8",
    )


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

    baseline_ids = load_baseline_ids()

    def match_filter(info: dict, *, incomplete: bool) -> str | None:
        video_id = info.get("id")
        if video_id and video_id in baseline_ids:
            return None
        return info.get("title") or "video"

    pending_count, pending_ids = count_pending_downloads()
    print(f"Nouvelles vidéos à télécharger : {pending_count}")
    if pending_count == 0:
        print("Aucune nouvelle vidéo détectée. Synchronisation terminée.")
        return

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "download_archive": str(ARCHIVE_FILE),
        "match_filter": match_filter,
        "ignoreerrors": True,
        "noplaylist": False,
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": AUDIO_QUALITY,
            },
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "postprocessor_args": {
            "EmbedThumbnail": ["-c:v", "mjpeg"],
        },
        "quiet": False,
        "no_warnings": False,
    }

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
