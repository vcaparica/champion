"""
dj.py - Sound Manager for Champion
===================================
Wraps OpenAL for SFX and BGM playback with panning, crossfade, and volume control.
"""

import os
import time
import threading
import wave
from typing import Dict, List, Optional, Tuple, Union

import openal

try:
    import pyogg  # type: ignore
except Exception:
    pyogg = None


Vec3 = Tuple[float, float, float]
SoundKey = Union[int, str]


class DJ:
    """Sound manager for videogame/audiogame development.

    Wraps the local `openal.py` wrapper to provide simple SFX/BGM playback
    and utilities like crossfade, panning, and volume control.

    Notes about OpenAL wrapper expectations:
    - `openal.BufferSound.load()` expects *decoded PCM bytes*.
    - `openal.Player.play()` does NOT rewind/restart if already playing.
    """

    def __init__(
        self,
        sfx_folder: str = "snd/sfx",
        bgm_folder: str = "snd/bgm",
        default_format: str = ".ogg",
        bgm_volume: float = 1.0,
        sfx_volume: float = 0.5,
    ) -> None:
        # Normalize folders (accept with or without trailing slash)
        self.sfx_folder = os.path.normpath(sfx_folder)
        self.bgm_folder = os.path.normpath(bgm_folder)

        # Default extension used when a caller passes a bare name.
        self.default_format = default_format.lower()

        self.bgm_volume = self._clamp_volume(bgm_volume)
        self.sfx_volume = self._clamp_volume(sfx_volume)

        # OpenAL listener
        self.listener = openal.Listener()
        self.listener.position = (0.0, 0.0, 0.0)

        # Loaded sounds and players
        self.sfx_players: List[openal.Player] = []
        self.bgm_players: List[openal.Player] = []
        self.sfx: List[openal.BufferSound] = []
        self.bgm: List[openal.BufferSound] = []

        # Deterministic file ordering + quick name lookup
        self._sfx_files: List[str] = []
        self._bgm_files: List[str] = []
        self._sfx_name_to_index: Dict[str, int] = {}
        self._bgm_name_to_index: Dict[str, int] = {}

        self.current_bgm_index = -1
        self.current_sfx_index = -1

    # ---------------------------------------------------------------------
    # Loading
    # ---------------------------------------------------------------------

    def load_sfx(self, extensions: Tuple[str, ...] = (".ogg", ".wav")) -> None:
        """Load all SFX files from the SFX folder.

        Creates 1 Player per sound (simple, deterministic). If you need
        polyphony (same sound overlapping), add multiple Players per sound.
        """
        self._load_folder(
            folder=self.sfx_folder,
            extensions=extensions,
            into_files="sfx",
        )

    def load_bgm(self, extensions: Tuple[str, ...] = (".ogg", ".wav")) -> None:
        """Load all BGM files from the BGM folder."""
        self._load_folder(
            folder=self.bgm_folder,
            extensions=extensions,
            into_files="bgm",
        )

    def _load_folder(self, folder: str, extensions: Tuple[str, ...], into_files: str) -> None:
        if not os.path.isdir(folder):
            # Keep it non-fatal (projects may ship without audio during dev)
            return

        extensions = tuple(ext.lower() for ext in extensions)
        files = [
            f
            for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(extensions)
        ]
        files.sort(key=lambda s: s.lower())

        if into_files == "sfx":
            # Clear any previous load to avoid leaking OpenAL resources.
            self._unload_group("sfx")
            self._sfx_files = files
            self._sfx_name_to_index = {}
            for idx, filename in enumerate(files):
                name = os.path.splitext(filename)[0]
                self._sfx_name_to_index[name.lower()] = idx
                sound, player = self._load_sound_and_player(os.path.join(folder, filename))
                self.sfx.append(sound)
                self.sfx_players.append(player)
        elif into_files == "bgm":
            self._unload_group("bgm")
            self._bgm_files = files
            self._bgm_name_to_index = {}
            for idx, filename in enumerate(files):
                name = os.path.splitext(filename)[0]
                self._bgm_name_to_index[name.lower()] = idx
                sound, player = self._load_sound_and_player(os.path.join(folder, filename))
                self.bgm.append(sound)
                self.bgm_players.append(player)
        else:
            raise ValueError("into_files must be 'sfx' or 'bgm'")

    def _load_sound_and_player(self, filepath: str) -> Tuple[openal.BufferSound, openal.Player]:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".ogg":
            if pyogg is None:
                raise RuntimeError(
                    "pyogg is required to load .ogg files. Install it or load .wav instead."
                )
            vorbis = pyogg.VorbisFile(filepath)
            pcm_bytes = vorbis.buffer
            channels = int(vorbis.channels)
            samplerate = int(vorbis.frequency)
            bitrate = 16  # pyogg VorbisFile outputs 16-bit signed PCM
            length = int(vorbis.buffer_length)
        elif ext == ".wav":
            pcm_bytes, channels, samplerate, bitrate, length = self._decode_wav(filepath)
        else:
            raise ValueError(f"Unsupported audio format: {ext}")

        snd = openal.BufferSound()
        snd.channels = channels
        snd.samplerate = samplerate
        snd.bitrate = bitrate
        snd.length = length
        snd.load(pcm_bytes)

        player = openal.Player()
        player.position = (0.0, 0.0, 0.0)
        player.rolloff = 0.01
        player.add(snd)

        return snd, player

    def _decode_wav(self, filepath: str) -> Tuple[bytes, int, int, int, int]:
        with wave.open(filepath, "rb") as wf:
            channels = int(wf.getnchannels())
            sampwidth = int(wf.getsampwidth())
            samplerate = int(wf.getframerate())
            nframes = int(wf.getnframes())
            pcm = wf.readframes(nframes)

        bitrate = sampwidth * 8
        length = len(pcm)
        return pcm, channels, samplerate, bitrate, length

    def _unload_group(self, group: str) -> None:
        if group == "sfx":
            for p in self.sfx_players:
                try:
                    p.delete()
                except Exception:
                    pass
            for s in self.sfx:
                try:
                    s.delete()
                except Exception:
                    pass
            self.sfx_players.clear()
            self.sfx.clear()
            self.current_sfx_index = -1
        elif group == "bgm":
            for p in self.bgm_players:
                try:
                    p.delete()
                except Exception:
                    pass
            for s in self.bgm:
                try:
                    s.delete()
                except Exception:
                    pass
            self.bgm_players.clear()
            self.bgm.clear()
            self.current_bgm_index = -1
        else:
            raise ValueError("group must be 'sfx' or 'bgm'")

    # ---------------------------------------------------------------------
    # Playback helpers
    # ---------------------------------------------------------------------

    def play_sfx(self, sfx: SoundKey, looped: bool = False, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> int:
        """Play a SFX by index or name.

        - If already playing, it is stopped+rewound so it restarts.
        - Returns the resolved SFX index, or -1 if not found.
        """
        idx = self._resolve_sfx(sfx)
        if idx < 0 or idx >= len(self.sfx_players):
            return -1

        player = self.sfx_players[idx]

        # Restart semantics (OpenAL Player.play does not rewind automatically)
        if player.playing():
            player.stop()
            player.rewind()

        player.position = (float(x), float(y), float(z))
        player.loop = bool(looped)
        player.volume = self.sfx_volume
        player.play()

        self.current_sfx_index = idx
        return idx

    def play_bgm(self, bgm: SoundKey, looped: bool = True) -> int:
        """Play a BGM by index or name.

        Returns the resolved BGM index, or -1 if not found.
        """
        idx = self._resolve_bgm(bgm)
        if idx < 0 or idx >= len(self.bgm_players):
            return -1

        player = self.bgm_players[idx]

        # Restart semantics
        if player.playing():
            player.stop()
            player.rewind()

        player.position = (0.0, 0.0, 0.0)
        player.volume = self.bgm_volume
        player.loop = bool(looped)
        player.play()

        self.current_bgm_index = idx
        return idx

    def stop_bgm(self, bgm: Optional[SoundKey] = None) -> None:
        idx = self.current_bgm_index if bgm is None else self._resolve_bgm(bgm)
        if 0 <= idx < len(self.bgm_players):
            self.bgm_players[idx].stop()

    def stop_sfx(self, sfx: SoundKey) -> None:
        idx = self._resolve_sfx(sfx)
        if 0 <= idx < len(self.sfx_players):
            self.sfx_players[idx].stop()

    def pause_bgm(self, bgm: Optional[SoundKey] = None) -> None:
        idx = self.current_bgm_index if bgm is None else self._resolve_bgm(bgm)
        if 0 <= idx < len(self.bgm_players):
            self.bgm_players[idx].pause()

    def pause_sfx(self, sfx: SoundKey) -> None:
        idx = self._resolve_sfx(sfx)
        if 0 <= idx < len(self.sfx_players):
            self.sfx_players[idx].pause()

    # ---------------------------------------------------------------------
    # Volume / panning
    # ---------------------------------------------------------------------

    @staticmethod
    def _clamp_volume(volume: float) -> float:
        if volume < 0.0:
            return 0.0
        if volume > 1.0:
            return 1.0
        return float(volume)

    def set_bgm_master_volume(self, new_volume: float) -> None:
        self.bgm_volume = self._clamp_volume(new_volume)
        if 0 <= self.current_bgm_index < len(self.bgm_players):
            self.bgm_players[self.current_bgm_index].volume = self.bgm_volume

    def set_sfx_master_volume(self, new_volume: float) -> None:
        self.sfx_volume = self._clamp_volume(new_volume)

    def set_bgm_volume(self, bgm: SoundKey, new_volume: float, change_time_ms: int = 0) -> None:
        """Set BGM volume for a specific track with optional fade."""
        idx = self._resolve_bgm(bgm)
        if not (0 <= idx < len(self.bgm_players)):
            return

        player = self.bgm_players[idx]
        target = self._clamp_volume(new_volume)

        if change_time_ms <= 0:
            player.volume = target
            return

        duration = change_time_ms / 1000.0
        initial = float(player.volume)
        start = time.time()

        while (time.time() - start) < duration:
            elapsed = time.time() - start
            frac = min(1.0, elapsed / duration)
            player.volume = initial + (target - initial) * frac
            time.sleep(0.01)

        player.volume = target

    def set_sfx_volume(self, sfx: SoundKey, new_volume: float) -> None:
        idx = self._resolve_sfx(sfx)
        if 0 <= idx < len(self.sfx_players):
            self.sfx_players[idx].volume = self._clamp_volume(new_volume)

    def set_sfx_panning(self, sfx: SoundKey, final_pan: float, panning_duration_ms: int = 0) -> None:
        """Pan a SFX along X: -1.0 left, 0.0 center, 1.0 right."""
        idx = self._resolve_sfx(sfx)
        if not (0 <= idx < len(self.sfx_players)):
            return

        player = self.sfx_players[idx]
        initial_pan = float(player.position[0]) if hasattr(player, "position") else 0.0
        target_pan = float(final_pan)

        if panning_duration_ms <= 0:
            player.position = (target_pan, 0.0, 0.0)
            return

        duration = panning_duration_ms / 1000.0
        start = time.time()

        while (time.time() - start) < duration:
            elapsed = time.time() - start
            frac = min(1.0, elapsed / duration)
            current_pan = initial_pan + (target_pan - initial_pan) * frac
            player.position = (current_pan, 0.0, 0.0)
            time.sleep(0.01)

        player.position = (target_pan, 0.0, 0.0)

    # ---------------------------------------------------------------------
    # Crossfading
    # ---------------------------------------------------------------------

    def bgm_crossfade(self, current_bgm: SoundKey, next_bgm: SoundKey, change_time_ms: int) -> None:
        """Crossfade between two BGM tracks (fade out current, fade in next)."""
        cur = self._resolve_bgm(current_bgm)
        nxt = self._resolve_bgm(next_bgm)
        if not (0 <= cur < len(self.bgm_players)) or not (0 <= nxt < len(self.bgm_players)):
            return

        next_player = self.bgm_players[nxt]

        # Start next at 0 if not already playing
        if not next_player.playing():
            next_player.volume = 0.0
            next_player.loop = True
            next_player.play()

        t1 = threading.Thread(target=self.set_bgm_volume, args=(cur, 0.0, change_time_ms))
        t2 = threading.Thread(target=self.set_bgm_volume, args=(nxt, self.bgm_volume, change_time_ms))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.bgm_players[cur].stop()
        self.current_bgm_index = nxt

    def bgm_next(self, crossfade_ms: int = 1000) -> None:
        if not self.bgm_players:
            return
        if self.current_bgm_index < 0:
            self.play_bgm(0, looped=True)
            return
        nxt = (self.current_bgm_index + 1) % len(self.bgm_players)
        self.bgm_crossfade(self.current_bgm_index, nxt, crossfade_ms)

    def bgm_previous(self, crossfade_ms: int = 1000) -> None:
        if not self.bgm_players:
            return
        if self.current_bgm_index < 0:
            self.play_bgm(0, looped=True)
            return
        prv = (self.current_bgm_index - 1) % len(self.bgm_players)
        self.bgm_crossfade(self.current_bgm_index, prv, crossfade_ms)

    # ---------------------------------------------------------------------
    # Lookup helpers (index or name)
    # ---------------------------------------------------------------------

    def _normalize_name(self, name: str) -> str:
        name = name.strip()
        base, ext = os.path.splitext(name)
        if ext:
            return base.lower()
        return name.lower()

    def _resolve_sfx(self, key: SoundKey) -> int:
        if isinstance(key, int):
            return key
        norm = self._normalize_name(key)
        return self._sfx_name_to_index.get(norm, -1)

    def _resolve_bgm(self, key: SoundKey) -> int:
        if isinstance(key, int):
            return key
        norm = self._normalize_name(key)
        return self._bgm_name_to_index.get(norm, -1)

    def get_sfx_by_name(self, name: str) -> int:
        return self._resolve_sfx(name)

    def get_bgm_by_name(self, name: str) -> int:
        return self._resolve_bgm(name)

    # ---------------------------------------------------------------------
    # Status + bulk operations
    # ---------------------------------------------------------------------

    def is_bgm_playing(self, bgm: Optional[SoundKey] = None) -> bool:
        idx = self.current_bgm_index if bgm is None else self._resolve_bgm(bgm)
        return bool(0 <= idx < len(self.bgm_players) and self.bgm_players[idx].playing())

    def is_sfx_playing(self, sfx: SoundKey) -> bool:
        idx = self._resolve_sfx(sfx)
        return bool(0 <= idx < len(self.sfx_players) and self.sfx_players[idx].playing())

    def stop_all_sfx(self) -> None:
        for p in self.sfx_players:
            p.stop()

    def stop_all_bgm(self) -> None:
        for p in self.bgm_players:
            p.stop()
        self.current_bgm_index = -1

    # ---------------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------------

    def cleanup(self) -> None:
        """Stop and delete all OpenAL resources owned by this DJ."""
        # Stop & delete players first (they reference buffers)
        for p in self.sfx_players:
            try:
                p.delete()
            except Exception:
                pass
        for p in self.bgm_players:
            try:
                p.delete()
            except Exception:
                pass

        # Delete buffers
        for s in self.sfx:
            try:
                s.delete()
            except Exception:
                pass
        for s in self.bgm:
            try:
                s.delete()
            except Exception:
                pass

        self.sfx_players.clear()
        self.bgm_players.clear()
        self.sfx.clear()
        self.bgm.clear()

        self._sfx_files.clear()
        self._bgm_files.clear()
        self._sfx_name_to_index.clear()
        self._bgm_name_to_index.clear()

        self.current_bgm_index = -1
        self.current_sfx_index = -1
