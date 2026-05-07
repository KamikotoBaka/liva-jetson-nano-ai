import numpy as np
import pickle
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

_encoder = None

_PROJECT_DIR = Path(__file__).resolve().parent
_VOICEPRINTS_DIR = _PROJECT_DIR / "data" / "voiceprints"
 
def _get_encoder_and_preprocess():
    global _encoder
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "resemblyzer is missing. Install it using: "
            "pip install resemblyzer webrtcvad-wheels"
        ) from exc
 
    if _encoder is None:
        _encoder = VoiceEncoder()
 
    return _encoder, preprocess_wav
 
 
# ── Profile Cache ─────────────────────────────────────────────────────────────
 
_PROFILES_CACHE: list[dict] | None = None
 
def _load_profiles() -> list[dict]:
    global _PROFILES_CACHE
 
    if _PROFILES_CACHE is not None:
        return _PROFILES_CACHE
 
    profiles = []
    profile_dir = _VOICEPRINTS_DIR
 
    if profile_dir.exists():
        for path in profile_dir.glob("*.pkl"):
            try:
                with open(path, "rb") as f:
                    profiles.append(pickle.load(f))
            except Exception as e:
                print(f"⚠️  Profile could not be loaded "
                      f"({path.name}): {e}")
 
    _PROFILES_CACHE = profiles
    return _PROFILES_CACHE
 
 
def invalidate_profile_cache():
    global _PROFILES_CACHE
    _PROFILES_CACHE = None
 
 
def get_enrolled_users() -> list[dict]:
    return [
        {"name": p["name"], "role": p["role"]}
        for p in _load_profiles()
    ]
 
 
# ── Audio Loader ──────────────────────────────────────────────────────────────
 
def _load_audio_from_file(audio_path: str,target_sr: int = 16000) -> np.ndarray:
    try:
        import av
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyAV is missing. Install it using: pip install av"
        ) from exc
 
    try:
        container = av.open(audio_path)
    except Exception as exc:
        raise RuntimeError(
            f"Audio file could not be opened: {exc}"
        ) from exc
 
    resampler = av.audio.resampler.AudioResampler(
        format="fltp",
        layout="mono",
        rate=target_sr,
    )
 
    chunks: list[np.ndarray] = []
 
    try:
        for frame in container.decode(audio=0):
            resampled = resampler.resample(frame)
            if not isinstance(resampled, list):
                resampled = [resampled]
            for out_frame in resampled:
                if out_frame is None:
                    continue
                samples = (out_frame.to_ndarray()
                           .astype(np.float32)
                           .reshape(-1))
                if samples.size > 0:
                    chunks.append(samples)
    except Exception as exc:
        raise RuntimeError(
            f"Audio could not be decoded: {exc}"
        ) from exc
    finally:
        container.close()
 
    if not chunks:
        raise RuntimeError(
            "No audio samples found in the file"
        )
 
    return np.concatenate(chunks)
 
 
# ── Berechtigungen ────────────────────────────────────────────────────────────
 
PERMISSIONS: dict[str, list[str] | str] = {
    "admin": [
        "identify_error",
        "restart_service",
        "restart_machine",
        "open_log",
        "download_log",
        "system_status",
        "open_spotify",
        "open_outlook",
        "open_teams",
        "custom_command",
        "good_morning",
        "what_happened_today",
    ],         
    "operator": [
        "identify_error",
        "open_log",
        "system_status",
        "custom_command",
    ],
    "guest":    [],
}
 
 
def can_execute(speaker: dict, intent: str) -> bool:
    allowed = PERMISSIONS.get(speaker.get("role", "guest"), [])
    if allowed == "*":
        return True
    return intent in allowed
 
 
# ── Kern: Embedding → Profil-Matching ────────────────────────────────────────
 
def _match_embedding(embedding: np.ndarray,
                     threshold: float = 0.72) -> dict:
    profiles = _load_profiles()
    
    if not profiles:
        return {"name": "Unknown", "role": "guest", 
                "confidence": 0.0}
    profile_embeddings = np.array(
        [p["embedding"] for p in profiles]
    )
    norms = np.linalg.norm(profile_embeddings, axis=1)
    emb_norm = np.linalg.norm(embedding)
    
    scores = profile_embeddings @ embedding / (norms * emb_norm)
    
    best_idx   = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    best_match = profiles[best_idx]
    
    if best_score >= threshold:
        return {
            "name":       best_match["name"],
            "role":       best_match["role"],
            "confidence": round(best_score, 3),
            "timestamp":  datetime.now().isoformat(),
        }
    
    return {
        "name":       "Unknown",
        "role":       "guest", 
        "confidence": round(best_score, 3),
        "timestamp":  datetime.now().isoformat(),
    }


def _get_best_match(embedding: np.ndarray) -> dict:
    profiles = _load_profiles()
    if not profiles:
        return {
            "name": "Unknown",
            "role": "guest",
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    profile_embeddings = np.array([p["embedding"] for p in profiles])
    norms = np.linalg.norm(profile_embeddings, axis=1)
    emb_norm = np.linalg.norm(embedding)
    if emb_norm == 0:
        return {
            "name": "Unknown",
            "role": "guest",
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    scores = profile_embeddings @ embedding / (norms * emb_norm)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    best_match = profiles[best_idx]
    return {
        "name": best_match["name"],
        "role": best_match["role"],
        "confidence": round(best_score, 3),
        "timestamp": datetime.now().isoformat(),
    }


def _get_threshold(env_name: str, default: float) -> float:
    raw = os.getenv(env_name)
    if not raw and env_name == "VOICE_AUTH_FILE_THRESHOLD":
        # Backward compatibility for users setting THRESHOLD directly.
        raw = os.getenv("THRESHOLD")
    if not raw:
        return default

    try:
        value = float(raw)
    except ValueError:
        return default

    return max(0.0, min(1.0, value))
 
 
# ── Öffentliche API ───────────────────────────────────────────────────────────
 
def identify_speaker(audio: np.ndarray,threshold: float = 0.72) -> dict:

    encoder, preprocess_wav = _get_encoder_and_preprocess()
    wav       = preprocess_wav(audio, source_sr=16000)
    embedding = encoder.embed_utterance(wav)
    return _match_embedding(embedding, threshold)
 
 
def identify_speaker_from_file(audio_path: str,
                                threshold: float | None = None) -> dict:
    effective_threshold = threshold
    if effective_threshold is None:
        # Browser-recorded clips are often shorter/noisier than local mic test audio.
        effective_threshold = _get_threshold("VOICE_AUTH_FILE_THRESHOLD", 0.58)

    encoder, preprocess_wav = _get_encoder_and_preprocess()
    audio = _load_audio_from_file(audio_path, target_sr=16000)
    wav   = preprocess_wav(audio, source_sr=16000)

    # Evaluate both variants and keep the stronger confidence.
    candidates: list[dict] = []

    try:
        embedding_speaker = encoder.embed_speaker([wav])
        candidates.append(_get_best_match(embedding_speaker))
    except Exception:
        pass

    try:
        embedding_utterance = encoder.embed_utterance(wav)
        candidates.append(_get_best_match(embedding_utterance))
    except Exception:
        pass

    if not candidates:
        return {
            "name": "Unknown",
            "role": "guest",
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    best = max(candidates, key=lambda item: float(item.get("confidence", 0.0)))
    if float(best.get("confidence", 0.0)) >= float(effective_threshold):
        return best

    return {
        "name": "Unknown",
        "role": "guest",
        "confidence": float(best.get("confidence", 0.0)),
        "timestamp": datetime.now().isoformat(),
    }
 
# ── Schnell-Test ──────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    import sounddevice as sd
    import time
 
    SAMPLE_RATE = 16000
    DURATION    = 3.0
 
    print("\n🎤 LIVA – Voice Recognition Test")
    print("─" * 35)
    enrolled = get_enrolled_users()
    if not enrolled:
        print("⚠️  No profiles found. "
              "Please run enroll.py first.")
    else:
        print("📋 Enrolled Users:")
        for u in enrolled:
            print(f"   • {u['name']} ({u['role']})")
 
    print()
    input("Press Enter and speak...")
 
    # ── Aufnahme ──────────────────────────────────────────
    t_start = time.perf_counter()
 
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    t_record = time.perf_counter()
 
    # ── Erkennung ─────────────────────────────────────────
    speaker = identify_speaker(audio.flatten())
    t_done  = time.perf_counter()
 
    # ── Ergebnis ──────────────────────────────────────────
    print(f"\n👤 Identified:    {speaker['name']}")
    print(f"🔑 Role:      {speaker['role']}")
    print(f"📊 Confidence:  {speaker['confidence']}")
    print(f"⏱️  Recording:   "
          f"{(t_record - t_start) * 1000:.0f} ms")
    print(f"⏱️  Identification:  "
          f"{(t_done - t_record) * 1000:.0f} ms")
    print(f"⏱️  Total:     "
          f"{(t_done - t_start) * 1000:.0f} ms")
 
    if speaker["role"] == "guest":
        print("\n❌ Access denied – Voice not recognized")
    else:
        print(f"\n✅ Welcome, {speaker['name']}!")
 
        # Berechtigungstest
        print("\n🔒 Permissions:")
        for intent in ["identify_error",
                       "restart_machine",
                       "open_spotify"]:
            ok   = can_execute(speaker, intent)
            icon = "✅" if ok else "❌"
            print(f"   {icon} {intent}")