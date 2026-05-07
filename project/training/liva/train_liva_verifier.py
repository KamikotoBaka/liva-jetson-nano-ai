from __future__ import annotations

import argparse
import glob
from pathlib import Path

from openwakeword.custom_verifier_model import train_custom_verifier


def collect_wavs(path: Path) -> list[str]:
    return sorted(glob.glob(str(path / "*.wav")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a LIVA verifier model with openwakeword.")
    parser.add_argument("--positive", required=True, help="Prepared positive_train directory")
    parser.add_argument("--negative", required=True, help="Prepared negative_train directory")
    parser.add_argument("--output", required=True, help="Output .pkl verifier path")
    parser.add_argument(
        "--base-model",
        default="alexa",
        choices=["alexa", "hey_jarvis", "hey_mycroft", "hey_rhasspy", "timer", "weather"],
        help="Pretrained wakeword model used as the base detector",
    )
    parser.add_argument("--threshold", type=float, default=0.25, help="Feature collection threshold")
    args = parser.parse_args()

    positive_dir = Path(args.positive).resolve()
    negative_dir = Path(args.negative).resolve()
    output_path = Path(args.output).resolve()

    positive_files = collect_wavs(positive_dir)
    negative_files = collect_wavs(negative_dir)

    if len(positive_files) < 20:
        print("Need at least 20 positive train clips.")
        return 1
    if len(negative_files) < 40:
        print("Need at least 40 negative train clips.")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    train_custom_verifier(
        positive_reference_clips=positive_files,
        negative_reference_clips=negative_files,
        output_path=str(output_path),
        model_name=args.base_model,
        threshold=args.threshold,
        inference_framework="onnx",
    )

    print(f"Verifier model saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
