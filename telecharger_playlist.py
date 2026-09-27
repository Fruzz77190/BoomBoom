#!/usr/bin/env python3
"""Télécharge les nouvelles vidéos d'une playlist YouTube en MP3 avec pochette."""

from __future__ import annotations

import argparse
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
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_FILE = SCRIPT_DIR / "cookies.txt"
ARCHIVE_FILE = DOWNLOAD_DIR / "archive.txt"
BASELINE_FILE = DOWNLOAD_DIR / ".baseline_done"
BASELINE_IDS_FILE = DOWNLOAD_DIR / "baseline_ids.txt"
AUDIO_QUALITY = "320"
THUMB_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}
# Videos connues comme privees / indisponibles (ne pas retenter).
SKIP_VIDEO_IDS = {"-ed8q6o0Bsc"}
COOKIE_BROWSERS = ("edge", "chrome", "firefox", "brave")


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


def apply_youtube_extract_opts(opts: dict, *, clients: list[str] | None = None) -> None:
    opts["extractor_args"] = {
        "youtube": {
            "player_client": clients or ["android", "web", "mweb", "tv_embedded"],
        }
    }
    opts["remote_components"] = ["ejs:github"]


def build_ydl_opts(
    *,
    match_filter=None,
    browser: str | None = None,
    cookiefile: str | None = None,
    with_thumbnail: bool = False,
    use_archive: bool = True,
    clients: list[str] | None = None,
) -> dict:
    postprocessors: list[dict] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": AUDIO_QUALITY,
        },
        {"key": "FFmpegMetadata"},
    ]
    if with_thumbnail:
        postprocessors.extend(
            [
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "EmbedThumbnail"},
            ]
        )

    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "ignoreerrors": False,
        "noplaylist": True,
        "writethumbnail": with_thumbnail,
        "keepvideo": False,
        "postprocessors": postprocessors,
        "quiet": False,
        "no_warnings": False,
    }
    if use_archive:
        opts["download_archive"] = str(ARCHIVE_FILE)
    if with_thumbnail:
        opts["postprocessor_args"] = {"EmbedThumbnail": ["-c:v", "mjpeg"]}

    apply_youtube_extract_opts(opts, clients=clients)
    if browser:
        opts["cookiesfrombrowser"] = (browser,)
    if cookiefile:
        opts["cookiefile"] = cookiefile
    if match_filter is not None:
        opts["match_filter"] = match_filter
    return opts


def download_strategies() -> list[dict]:
    strategies: list[dict] = []
    if COOKIES_FILE.exists():
        strategies.append(
            {
                "label": "cookies.txt",
                "cookiefile": str(COOKIES_FILE),
                "clients": ["android", "web", "mweb"],
            }
        )
    for browser in COOKIE_BROWSERS:
        strategies.append(
            {
                "label": f"cookies {browser}",
                "browser": browser,
                "clients": ["android", "web", "mweb"],
            }
        )
        strategies.append(
            {
                "label": f"cookies {browser} (tv_embedded)",
                "browser": browser,
                "clients": ["tv_embedded", "android"],
            }
        )
    strategies.append(
        {
            "label": "sans cookies (android)",
            "clients": ["android", "web"],
        }
    )
    return strategies


def try_create_youtube_dl(strategy: dict, *, match_filter=None, noplaylist: bool = True):
    opts = build_ydl_opts(
        match_filter=match_filter,
        browser=strategy.get("browser"),
        cookiefile=strategy.get("cookiefile"),
        with_thumbnail=False,
        use_archive=False,
        clients=strategy.get("clients"),
    )
    opts["noplaylist"] = noplaylist
    return yt_dlp.YoutubeDL(opts)


def download_urls_with_strategies(
    urls: list[str],
    entries: list[dict],
    *,
    label: str,
    use_archive_after_success: bool = True,
) -> int:
    if not urls:
        return 0

    by_id = entries_by_id(entries)
    video_ids = [url.rsplit("=", 1)[-1] for url in urls]
    print(f"\n{label} : {len(urls)} video(s)")
    print(f"Dossier MP3 : {DOWNLOAD_DIR}")
    print("(Les MP3 ne vont PAS dans le dossier BoomBoom du projet.)\n")

    errors = 0
    for url in urls:
        video_id = url.rsplit("=", 1)[-1]
        entry = by_id.get(video_id, {})
        title = entry.get("title", video_id)
        print(f"--- {title} ---")

        if mp3_path_for_entry(entry).exists():
            print("MP3 deja present, ignore.")
            continue

        success = False
        for strategy in download_strategies():
            print(f"Essai : {strategy['label']}")
            try:
                with try_create_youtube_dl(strategy) as ydl:
                    result = ydl.download([url])
                if result not in (0, None) and result is not False:
                    print(f"  yt-dlp a signale {result} erreur(s)")
            except Exception as exc:
                print(f"  Echec : {exc}")
                continue

            if mp3_path_for_entry(entry).exists():
                print("  OK — MP3 telecharge.")
                success = True
                if use_archive_after_success:
                    with ARCHIVE_FILE.open("a", encoding="utf-8") as archive:
                        archive.write(f"youtube {video_id}\n")
                break
            print("  Pas de MP3 cree, strategie suivante...")

        if not success:
            errors += 1
            print("ECHEC pour cette video.")

    finalize_download_attempt(set(video_ids), entries)
    return errors


def fetch_playlist_entries() -> list[dict]:
    ydl_opts: dict = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "ignoreerrors": True,
    }
    apply_youtube_extract_opts(ydl_opts)
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


def entries_by_id(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries if entry.get("id")}


def mp3_path_for_entry(entry: dict) -> Path:
    title = entry.get("title") or entry.get("id") or "video"
    return DOWNLOAD_DIR / f"{title_to_stem(title)}.mp3"


def finalize_download_attempt(video_ids: set[str], entries: list[dict]) -> None:
    """Retire de l'archive les videos sans MP3 et supprime les pochettes orphelines."""
    by_id = entries_by_id(entries)
    failed: set[str] = set()

    for video_id in video_ids:
        entry = by_id.get(video_id)
        if not entry:
            continue
        if not mp3_path_for_entry(entry).exists():
            failed.add(video_id)

    if not failed:
        return

    remove_ids_from_archive(failed)
    cleanup_orphan_thumbnails()
    print(
        f"\n{len(failed)} telechargement(s) echoue(s) — non enregistre(s) dans l'archive."
    )
    print(
        "Si vous voyez 'HTTP 403' :"
        "\n  1. Connectez-vous a YouTube dans Edge/Chrome"
        "\n  2. Fermez le navigateur"
        "\n  3. Ajoutez cookies.txt (voir COOKIES_README.txt)"
        "\n  4. Relancez reparer_mp3_manquants.bat"
    )
    for video_id in sorted(failed):
        title = by_id.get(video_id, {}).get("title", video_id)
        if video_id in SKIP_VIDEO_IDS:
            print(f"  - {title} (video privee / ignoree)")
        else:
            print(f"  - {title}")


def download_video_urls(urls: list[str], *, label: str, entries: list[dict]) -> int:
    return download_urls_with_strategies(
        urls,
        entries,
        label=label,
        use_archive_after_success=True,
    )


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

    skipped = video_ids & SKIP_VIDEO_IDS
    if skipped:
        print(f"Ignorées (privées / indisponibles) : {', '.join(sorted(skipped))}")
        cleanup_orphan_thumbnails()

    video_ids -= SKIP_VIDEO_IDS
    if not video_ids:
        return 0

    remove_ids_from_archive(video_ids)
    urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in sorted(video_ids)]
    return download_video_urls(
        urls,
        label="Retelechargement MP3 manquants",
        entries=entries,
    )


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

    pending_count, pending_ids = count_pending_downloads()
    print(f"Nouvelles vidéos à télécharger : {pending_count}")

    if pending_count == 0 and repair_errors == 0:
        print("Aucune nouvelle vidéo détectée. Synchronisation terminée.")
        return

    if pending_count == 0:
        print("Synchronisation terminée (reparation effectuee).")
        return

    print(f"Playlist : {PLAYLIST_URL}")
    print(f"Dossier  : {DOWNLOAD_DIR}")
    print(f"Archive  : {ARCHIVE_FILE}")
    print(f"Qualité  : MP3 {AUDIO_QUALITY} kbps")
    if pending_ids:
        print(f"IDs     : {', '.join(sorted(pending_ids)[:5])}"
              + (" ..." if len(pending_ids) > 5 else ""))
    print()

    entries = fetch_playlist_entries()
    pending_urls = [
        f"https://www.youtube.com/watch?v={video_id}"
        for video_id in sorted(pending_ids)
    ]
    errors = download_urls_with_strategies(
        pending_urls,
        entries,
        label="Nouvelles videos playlist",
        use_archive_after_success=True,
    )

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


def upgrade_ytdlp() -> None:
    import subprocess

    print("Mise a jour de yt-dlp...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
        check=False,
    )


def run_repair_only() -> int:
    upgrade_ytdlp()
    check_dependencies()
    ensure_baseline()
    errors = repair_incomplete_downloads()
    if errors:
        print(f"\nReparation terminee avec {errors} erreur(s).")
        return 1
    print("\nReparation terminee.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronise la playlist YouTube en MP3.")
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="Repare uniquement les pochettes sans MP3 (reparer_mp3_manquants.bat).",
    )
    args = parser.parse_args()

    try:
        if args.repair_only:
            return run_repair_only()
        check_dependencies()
        ensure_baseline()
        download_playlist()
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
