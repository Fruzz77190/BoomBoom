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


def load_archive_ids() -> set[str]:
    if not ARCHIVE_FILE.exists():
        return set()

    ids: set[str] = set()
    for line in ARCHIVE_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            ids.add(parts[1])
    return ids


def seed_archive(video_ids: set[str]) -> int:
    existing = load_archive_ids()
    new_ids = video_ids - existing

    if new_ids:
        with ARCHIVE_FILE.open("a", encoding="utf-8") as archive:
            for video_id in sorted(new_ids):
                archive.write(f"youtube {video_id}\n")

    return len(new_ids)


def ensure_baseline() -> None:
    if BASELINE_FILE.exists():
        return

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print("Initialisation : marquage des vidéos déjà présentes dans la playlist...")
    playlist_ids = fetch_playlist_ids()
    added = seed_archive(playlist_ids)
    BASELINE_FILE.write_text(
        f"{len(playlist_ids)} vidéos ignorées à partir du {date.today()}\n",
        encoding="utf-8",
    )
    print(
        f"{added} video(s) ajoutee(s) a l'archive "
        f"({len(playlist_ids)} au total dans la playlist)."
    )
    print("Seules les vidéos ajoutées désormais seront téléchargées.\n")


def download_playlist() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "download_archive": str(ARCHIVE_FILE),
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
