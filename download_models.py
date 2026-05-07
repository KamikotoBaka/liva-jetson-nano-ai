#!/usr/bin/env python3
"""
Download llama.cpp models using Python (more reliable than wget on some systems)
"""

import os
import sys
from pathlib import Path

def download_model(repo_id: str, model_name: str, dest_dir: str) -> bool:
    """Download a model from HuggingFace Hub"""
    dest_path = Path(dest_dir) / model_name
    
    if dest_path.exists():
        print(f"  ✓ Model already exists: {dest_path}")
        return True
    
    try:
        from huggingface_hub import hf_hub_download
        
        print(f"  Downloading {model_name}...")
        hf_hub_download(
            repo_id=repo_id,
            filename=model_name,
            local_dir=dest_dir,
            local_dir_use_symlinks=False
        )
        print(f"  ✓ Downloaded: {dest_path}")
        return True
        
    except ImportError:
        print("  ✗ huggingface_hub not installed")
        print("    Install with: pip install huggingface-hub")
        return False
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return False

def main():
    models_dir = Path("./models")
    models_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("LIVA Llama Model Downloader")
    print("=" * 60)
    print()
    
    # Model: Non-thinking LLM
    print("[1/1] LLM Model (Qwen 2.5 Instruct 1.5B)")
    print("      Size: ~1.0 GB")
    llm_ok = download_model(
        "cjpai/Qwen2.5-1.5B-Instruct-gguf",
        "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        str(models_dir)
    )
    print()
    
    # Summary
    print("=" * 60)
    if llm_ok:
        print("✓ LLM model downloaded successfully!")
        print()
        print("Models in ./models:")
        for f in sorted(models_dir.glob("*.gguf")):
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  {f.name:50} {size_mb:>8.1f} MB")
        print()
        print("Ready to deploy:")
        print("  docker compose up -d")
        return 0
    else:
        print("⚠ LLM model download failed")
        print()
        print("Troubleshooting:")
        print("  1. Check internet: curl https://huggingface.co")
        print("  2. Install huggingface-hub: pip install -U huggingface-hub")
        print("  3. Try bash script: bash setup_models_llama.sh")
        print("  4. Manual download: https://huggingface.co/cjpai/Qwen2.5-1.5B-Instruct-gguf")
        return 1

if __name__ == "__main__":
    sys.exit(main())
