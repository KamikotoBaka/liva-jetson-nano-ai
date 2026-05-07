from __future__ import annotations

import argparse
import random
import shutil
import wave
from pathlib import Path


def is_valid_wav(path: Path) -> tuple[bool, str]:
    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            if channels != 1:
                return False, f"{path.name}: expected mono, got {channels} channels"
            if sample_width != 2:
                return False, f"{path.name}: expected 16-bit PCM, got {sample_width * 8}-bit"
            if sample_rate != 16000:
                return False, f"{path.name}: expected 16000 Hz, got {sample_rate} Hz"
    except wave.Error as exc:
        return False, f"{path.name}: invalid WAV ({exc})"
    except OSError as exc:
        return False, f"{path.name}: cannot read ({exc})"
    return True, "ok"


def split_copy(files: list[Path], train_dir: Path, test_dir: Path, test_ratio: float) -> tuple[int, int]:
    random.shuffle(files)
    split_idx = max(1, int(len(files) * (1.0 - test_ratio))) if len(files) > 1 else len(files)
    train_files = files[:split_idx]
    test_files = files[split_idx:]

    train_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    for idx, src in enumerate(train_files, start=1):
        shutil.copy2(src, train_dir / f"{idx:04d}_{src.name}")
    for idx, src in enumerate(test_files, start=1):
        shutil.copy2(src, test_dir / f"{idx:04d}_{src.name}")

    return len(train_files), len(test_files)


def clear_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and split LIVA wakeword dataset.")
    parser.add_argument("--positive", required=True, help="Folder with positive LIVA WAV clips")
    parser.add_argument("--negative", required=True, help="Folder with negative non-LIVA WAV clips")
    parser.add_argument("--out", required=True, help="Prepared output folder")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    positive_dir = Path(args.positive).resolve()
    negative_dir = Path(args.negative).resolve()
    out_dir = Path(args.out).resolve()

    if not positive_dir.exists() or not negative_dir.exists():
        print("Positive or negative directory does not exist.")
        return 1

    positive_files = sorted(positive_dir.glob("*.wav"))
    negative_files = sorted(negative_dir.glob("*.wav"))

    if len(positive_files) < 20:
        print("Need at least 20 positive clips for a useful model.")
        return 1
    if len(negative_files) < 40:
        print("Need at least 40 negative clips for a useful model.")
        return 1

    valid_positive: list[Path] = []
    valid_negative: list[Path] = []

    for path in positive_files:
        ok, reason = is_valid_wav(path)
        if ok:
            valid_positive.append(path)
        else:
            print(f"Skipping positive: {reason}")

    for path in negative_files:
        ok, reason = is_valid_wav(path)
        if ok:
            valid_negative.append(path)
        else:
            print(f"Skipping negative: {reason}")

    if len(valid_positive) < 20 or len(valid_negative) < 40:
        print("Not enough valid WAV files after validation.")
        return 1

    positive_train = out_dir / "positive_train"
    positive_test = out_dir / "positive_test"
    negative_train = out_dir / "negative_train"
    negative_test = out_dir / "negative_test"

    clear_dir(positive_train)
    clear_dir(positive_test)
    clear_dir(negative_train)
    clear_dir(negative_test)

    pos_train_count, pos_test_count = split_copy(valid_positive, positive_train, positive_test, args.test_ratio)
    neg_train_count, neg_test_count = split_copy(valid_negative, negative_train, negative_test, args.test_ratio)

    print("Dataset prepared:")
    print(f"  positive_train: {pos_train_count}")
    print(f"  positive_test: {pos_test_count}")
    print(f"  negative_train: {neg_train_count}")
    print(f"  negative_test: {neg_test_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
