import sounddevice as sd
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
import pickle
import threading
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
 
# ── Konfiguration ─────────────────────────────────────────────────────────────
 
SAMPLE_RATE  = 16000
RECORD_SECS  = 4.0      # länger als vorher (war 2.5)
NUM_SAMPLES  = 10       # mehr Samples (war 3)
 
encoder = VoiceEncoder()

PROJECT_DIR = Path(__file__).resolve().parent
VOICEPRINTS_DIR = PROJECT_DIR / "data" / "voiceprints"
 
# ── Sätze für Enrollment ──────────────────────────────────────────────────────
# Verschiedene Satztypen für ein stabiles Stimmmodell:
# Befehle, Fragen, Aussagen, Zahlen, kurze + lange Sätze
 
ENROLLMENT_SENTENCES = [
    # Runde 1 – LIVA Systembefehle (kurz)
    "Hey LIVA, show me the current system status.",
    "Identify error.",
    "System Status check.",
    "Log File open.",
    "Apache Server restart.",
 
    # Runde 2 – LIVA Systembefehle (länger)
    "Hey LIVA, show me the current status of all devices.",
    "Identify all errors in the system and create a report.",
    "Open the log file and show me the latest entries.",
    "Please check all connected devices in the network.",
    "Restart the service and verify if the connection is active.",
 
    # Runde 3 – Zahlen und technische Begriffe
    "Device number three reports an error since ten minutes.",
    "Temperature is at forty-two degrees Celsius.",
    "Process one two three has been completed successfully.",
    "Connection to IP address one nine two point one six eight.",
    "Error code five zero three has occurred.",
 
    # Runde 4 – Alltag (verschiedene Emotionen/Tempo)
    "Good morning, I am starting work now.",
    "The system is running stably, all connections are active.",
    "Please show me a summary of today's activities.",
    "The production process has been completed successfully.",
    "I would like to check the current machine status.",
]
 
# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
 
def _show_progress(duration: float):
    """Fortschrittsbalken während Aufnahme."""
    steps = int(duration * 10)
    for i in range(steps):
        filled    = int((i / steps) * 25)
        bar       = "█" * filled + "░" * (25 - filled)
        remaining = duration - (i * 0.1)
        sys.stdout.write(f"\r  🔴 [{bar}] {remaining:.1f}s ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r  ✅ Fertig!                              \n")
    sys.stdout.flush()
 
 
def record_audio(duration: float = RECORD_SECS) -> np.ndarray:
    """Aufnahme mit Fortschrittsbalken."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    t = threading.Thread(target=_show_progress, args=(duration,))
    t.start()
    sd.wait()
    t.join()
    return audio.flatten()
 
 
def compute_embedding(audio: np.ndarray) -> np.ndarray:
    """Stimmabdruck aus Audio berechnen."""
    wav = preprocess_wav(audio, source_sr=SAMPLE_RATE)
    try:
        return encoder.embed_speaker([wav])    # schneller
    except Exception:
        return encoder.embed_utterance(wav)    # Fallback
 
 
def _quality_check(embedding: np.ndarray,
                   all_embeddings: list) -> float:
    """
    Prüft wie konsistent die Aufnahmen sind.
    Gibt durchschnittliche Ähnlichkeit zurück (0-1).
    Unter 0.7 = schlechte Aufnahmequalität.
    """
    if len(all_embeddings) < 2:
        return 1.0
 
    scores = []
    for prev in all_embeddings[:-1]:
        score = float(
            np.dot(embedding, prev) /
            (np.linalg.norm(embedding) * np.linalg.norm(prev))
        )
        scores.append(score)
 
    return round(float(np.mean(scores)), 3)
 
 
# ── Haupt-Enrollment ──────────────────────────────────────────────────────────
 
def enroll_user(name: str, role: str):
    """
    Lernt eine neue Stimme ein.
    Empfohlen: 10-20 Sätze für beste Erkennung.
    """
    print(f"\n{'═' * 50}")
    print(f"  👤 LIVA – Voice Enrollment")
    print(f"{'═' * 50}")
    print(f"  Name:    {name}")
    print(f"  Role:   {role}")
    print(f"  Sentences:   {NUM_SAMPLES}")
    print(f"  Duration:   {RECORD_SECS} seconds each")
    print(f"{'─' * 50}")
    print()
    print("  📋 Tips for Optimal Detection:")
    print("  • Normal speaking – not too slow/fast")
    print("  • Normal distance to the microphone (~30cm)")
    print("  • Different volumes are good")
    print("  • Say the whole sentence, not just one word")
    print()
 
    input("  Press Enter to start...")
    print()
 
    raw_audios  = []
    embeddings  = []
    bad_samples = []
 
    for i, sentence in enumerate(ENROLLMENT_SENTENCES[:NUM_SAMPLES]):
        print(f"  [{i+1:02d}/{NUM_SAMPLES}] Speak this sentence:")
        print(f"  💬 \"{sentence}\"")
        print()
        input("  → Press Enter and speak...")
 
        audio     = record_audio()
        embedding = compute_embedding(audio)
 
        # Qualitätsprüfung
        embeddings.append(embedding)
        quality = _quality_check(embedding, embeddings)
 
        if quality < 0.65 and i > 0:
            print(f"  ⚠️  Low Quality ({quality}) – "
                  f"please repeat")
            bad_samples.append(i)
 
            # Nochmal aufnehmen
            input("  → Press Enter and speak again...")
            audio     = record_audio()
            embedding = compute_embedding(audio)
            embeddings[-1] = embedding
            quality   = _quality_check(embedding, embeddings[:-1])
            print(f"  📊 New Quality: {quality}")
        else:
            if i > 0:
                print(f"  📊 Consistency: {quality}")
 
        raw_audios.append(audio)
        print()
 
    # ── Alle Embeddings parallel berechnen ───────────────────
    print(f"  ⚙️  Process {NUM_SAMPLES} Recordings...")
 
    with ThreadPoolExecutor(max_workers=4) as pool:
        final_embeddings = list(pool.map(compute_embedding, raw_audios))
 
    # Durchschnitt = stabiles Profil
    mean_embedding = np.mean(final_embeddings, axis=0)
 
    # ── Qualitätsbericht ──────────────────────────────────────
    scores = []
    for emb in final_embeddings:
        score = float(
            np.dot(mean_embedding, emb) /
            (np.linalg.norm(mean_embedding) * np.linalg.norm(emb))
        )
        scores.append(score)
 
    avg_quality = round(float(np.mean(scores)), 3)
    min_quality = round(float(np.min(scores)), 3)
 
    print()
    print(f"{'─' * 50}")
    print(f"  📊 Quality Report:")
    print(f"     Average Consistency: {avg_quality}")
    print(f"     Lowest Value:             {min_quality}")
 
    if avg_quality >= 0.85:
        print(f"     Rating: ✅ Excellent!")
    elif avg_quality >= 0.75:
        print(f"     Rating: ✅ Good")
    elif avg_quality >= 0.65:
        print(f"     Rating: ⚠️  Acceptable – more samples recommended")
    else:
        print(f"     Rating: ❌ Poor – please repeat enrollment")
    # ── Profil speichern ──────────────────────────────────────
    profile = {
        "name":      name,
        "role":      role,
        "embedding": mean_embedding,
        "samples":   NUM_SAMPLES,
        "quality":   avg_quality,
    }
 
    VOICEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = VOICEPRINTS_DIR / f"{name}.pkl"
 
    with open(profile_path, "wb") as f:
        pickle.dump(profile, f)
 
    print(f"{'─' * 50}")
    print(f"  ✅ Profile for '{name}' ({role}) saved!")
    print(f"  📁 {profile_path}")
    print(f"{'═' * 50}\n")
 
 
def list_profiles():
    """Shows all enrolled profiles."""
    profiles_dir = VOICEPRINTS_DIR
    if not profiles_dir.exists():
        print("  ⚠️  No profiles found.")
        return
 
    files = list(profiles_dir.glob("*.pkl"))
    if not files:
        print("  ⚠️  No profiles found.")
        return
 
    print(f"\n  📋 Enrolled Users ({len(files)}):")
    for path in files:
        with open(path, "rb") as f:
            p = pickle.load(f)
        quality = p.get("quality", "?")
        samples = p.get("samples", "?")
        print(f"     • {p['name']:<15} "
              f"Role: {p['role']:<10} "
              f"Samples: {samples:<5} "
              f"Quality: {quality}")
    print()
 
 
def delete_profile(name: str):
    """Deletes a profile."""
    path = VOICEPRINTS_DIR / f"{name}.pkl"
    if path.exists():
        path.unlink()
        print(f"  ✅ Profile '{name}' deleted.")
    else:
        print(f"  ⚠️  Profile '{name}' not found.")
 
 
# ── Menü ──────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
 
    print(f"\n{'═' * 50}")
    print(f"  🎤 LIVA – Enrollment Tool")
    print(f"{'═' * 50}")
 
    list_profiles()
 
    print("  What would you like to do?")
    print("  [1] Enroll new user")
    print("  [2] Delete profile")
    print("  [3] Show profiles")
    print("  [4] Exit")
    print()
 
    choice = input("  Selection: ").strip()
 
    if choice == "1":
        print()
        name = input("  Name:  ").strip()
        print("  Roles: admin / operator / guest")
        role = input("  Role: ").strip().lower()
 
        if role not in ("admin", "operator", "guest"):
            print("  ⚠️  Invalid role. Please use: admin, operator, guest")
        elif not name:
            print("  ⚠️  Name cannot be empty.")
        else:
            enroll_user(name, role)
 
    elif choice == "2":
        list_profiles()
        name = input("  Name of the profile to be deleted: ").strip()
        delete_profile(name)
 
    elif choice == "3":
        list_profiles()
 
    else:
        print("  Goodbye!")