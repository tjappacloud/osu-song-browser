"""Metadata extraction and caching for audio files and osu! backgrounds."""

from pathlib import Path
from .utils import strip_leading_numbers

# Try to import mutagen for reading audio tags
try:
    from mutagen._file import File as MutagenFile
    HAS_MUTAGEN = True
except Exception:
    MutagenFile = None
    HAS_MUTAGEN = False

# Try to import pygame for duration fallback
try:
    import pygame.mixer
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


def get_mp3_metadata(path: Path) -> dict:
    """Return a small metadata dict for the audio file: title, artist, album, duration (seconds).
    Requires mutagen; returns empty dict if unavailable or on error.
    """
    if not HAS_MUTAGEN or MutagenFile is None:
        return {}

    try:
        # Try Easy interface first (maps common names like 'title', 'artist')
        audio_easy = MutagenFile(str(path), easy=True)
        meta = {}
        title = None
        artist = None
        album = None
        duration = None

        if audio_easy:
            try:
                title = audio_easy.get('title', [None])[0] if audio_easy.get('title') else None
                artist = audio_easy.get('artist', [None])[0] if audio_easy.get('artist') else None
                album = audio_easy.get('album', [None])[0] if audio_easy.get('album') else None
            except Exception:
                pass
            try:
                duration = int(audio_easy.info.length) if hasattr(audio_easy, 'info') and hasattr(audio_easy.info, 'length') else None
            except Exception:
                pass

        # If we didn't get a title, try raw tags (ID3 frames) for TIT2
        if not title:
            audio_raw = MutagenFile(str(path))
            if audio_raw and getattr(audio_raw, 'tags', None) is not None:
                try:
                    title = str(audio_raw.tags.get('TIT2', '')) or None
                except Exception:
                    pass

        # Fallback: use filename stem with numbers stripped
        if not title:
            title = strip_leading_numbers(path.stem)

        if title:
            meta['title'] = title
        if artist:
            meta['artist'] = artist
        if album:
            meta['album'] = album
        if duration:
            meta['duration'] = duration

        return meta
    except Exception:
        return {}


def get_osu_background(folder: Path) -> Path | None:
    """Find the first .osu file in folder and parse its [Events] section for a background image.
    Returns the resolved Path to the image if found and exists, otherwise None.

    Notes:
    - Ignores Video events and only returns image files referenced by background events.
    - Supports common image extensions: .jpg, .jpeg, .png, .bmp, .gif.
    """
    try:
        # find first .osu file
        osu_path = None
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() == '.osu':
                osu_path = p
                break
        if osu_path is None:
            return None

        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}

        with osu_path.open('r', encoding='utf-8', errors='ignore') as f:
            in_events = False
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith('[Events]'):
                    in_events = True
                    continue
                if in_events:
                    # End of events section
                    if stripped.startswith('['):
                        break
                    # Skip video lines explicitly
                    if stripped.startswith('Video,'):
                        continue
                    # Typical background line formats in [Events]:
                    # 0,0,"bg.jpg",0,0
                    # Background and Video event types can vary, we only accept images
                    parts = [p.strip() for p in stripped.split(',')]
                    if len(parts) >= 3:
                        candidate = parts[2].strip().strip('"')
                        if candidate:
                            # Normalize path separators and remove leading/trailing spaces/quotes
                            candidate_path = folder / candidate
                            # If not exists with relative path, try resolving from .osu parent folder anyway
                            if candidate_path.exists() and candidate_path.suffix.lower() in image_exts:
                                return candidate_path
            return None
    except Exception:
        return None


def ensure_duration(path: Path, metadata_dict: dict) -> int:
    """Ensure we have a cached duration (seconds) for `path` stored in metadata_dict.
    Tries Mutagen then pygame.mixer.Sound fallback.
    Returns duration in seconds (int) or 0 if unknown.
    Mutates metadata_dict to store duration.
    """
    key = str(path)
    meta = metadata_dict.get(key, {})
    dur = meta.get('duration') or 0
    if dur:
        return dur

    # Try mutagen first
    if HAS_MUTAGEN and MutagenFile is not None:
        try:
            audio = MutagenFile(str(path))
            if audio and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                length = int(audio.info.length or 0)
                if length:
                    meta['duration'] = length
                    metadata_dict[key] = meta
                    return length
        except Exception:
            pass

    # Fall back to pygame.mixer.Sound (may use more memory)
    if HAS_PYGAME:
        try:
            snd = pygame.mixer.Sound(str(path))
            length = int(snd.get_length() or 0)
            if length:
                meta['duration'] = length
                metadata_dict[key] = meta
                return length
        except Exception:
            pass

    return 0
