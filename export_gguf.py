#!/usr/bin/env python3
"""
export_gguf.py — quantize the merged critic model to GGUF for Ollama
====================================================================
Loads the merged 16-bit model and writes a quantized .gguf single file,
which is what Ollama / llama.cpp load. Q4_K_M is the sweet spot: ~5GB,
minimal quality loss, fits the 5070 with headroom.

Usage (venv active, from ~/hf-critic):
    python export_gguf.py
    python export_gguf.py --quant q5_k_m      # slightly larger, higher fidelity

Output:
    outputs/critic-qwen3-8b/gguf/<name>.<QUANT>.gguf

Note: the first GGUF export triggers Unsloth to build llama.cpp locally,
which takes several minutes and needs build tools. If it errors on a
missing compiler, run:  sudo apt install -y build-essential cmake
"""

import argparse
from pathlib import Path

from unsloth import FastLanguageModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="outputs/critic-qwen3-8b/final",
                    help="path to the merged 16-bit model")
    ap.add_argument("--out", default="outputs/critic-qwen3-8b/gguf")
    ap.add_argument("--quant", default="q4_k_m",
                    choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
                    help="quantization: q4_k_m ~5GB (default), q5_k_m ~5.6GB, "
                         "q8_0 ~8.5GB (near-lossless), f16 ~16GB (no quant)")
    ap.add_argument("--seq-len", type=int, default=2048)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading merged model from {args.model} ...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.seq_len,
        load_in_4bit=False,       # load full weights so we quantize cleanly
        dtype=None,
    )

    print(f"Exporting GGUF ({args.quant}) to {out} ...")
    # Unsloth handles the llama.cpp conversion + quantization in one call.
    model.save_pretrained_gguf(
        str(out),
        tokenizer,
        quantization_method=args.quant,
    )

    ggufs = list(out.glob("*.gguf"))
    print("\nDone. GGUF file(s):")
    for g in ggufs:
        print(f"  {g}  ({g.stat().st_size / 1e9:.1f} GB)")
    print("\nNext: create the Ollama Modelfile and run "
          "`ollama create critic -f Modelfile`")


if __name__ == "__main__":
    main()
