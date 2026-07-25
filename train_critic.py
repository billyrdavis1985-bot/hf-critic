#!/usr/bin/env python3
"""
train_critic.py — QLoRA fine-tune of Qwen3-8B on the reasoning-critic corpus
============================================================================
Runs on a single 12GB Blackwell GPU (RTX 5070) under WSL2.

Key design choices:
- 4-bit QLoRA: base weights frozen in NF4, only LoRA adapters train. An 8B
  model in 4-bit is ~5.5GB; adapters + activations + optimizer state fit the
  remaining headroom at seq_len 2048, batch 1, grad-accum 16.
- LOCAL UPSAMPLING: the 38 hudson-forge-original rows are ~0.5% of the corpus.
  Left as-is they'd be drowned out. We repeat them so they carry real weight
  in the loss without discarding the external data that teaches general
  critique fluency. Tune UPSAMPLE_FACTOR to trade specialization vs breadth.
- Eval on the held-out val split every N steps to catch overfitting early.

Usage (from ~/hf-critic, venv active):
    python train_critic.py
    python train_critic.py --upsample 25 --epochs 2 --seq-len 2048

Outputs:
    outputs/critic-qwen3-8b/          checkpoints + final adapter
    outputs/critic-qwen3-8b/final/    merged adapter ready to export
"""

import argparse
import json
from pathlib import Path

# Unsloth must be imported before transformers/trl to install its patches.
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from datasets import Dataset
from trl import SFTConfig, SFTTrainer


def load_corpus(train_path, val_path, upsample_factor):
    """Load JSONL, upsample local rows, return HF Datasets."""
    def read(p):
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    train_rows = read(train_path)
    val_rows = read(val_path)

    # Upsample only the user's own examples. Everything else stays x1.
    local = [r for r in train_rows if r["meta"]["source"] == "hudson-forge-original"]
    external = [r for r in train_rows if r["meta"]["source"] != "hudson-forge-original"]
    upsampled = local * upsample_factor

    print(f"corpus: {len(external)} external + {len(local)} local x{upsample_factor} "
          f"= {len(upsampled)} -> {len(external) + len(upsampled)} train rows")
    print(f"        local effective share: "
          f"{len(upsampled) / (len(external) + len(upsampled)):.1%}")

    train = external + upsampled
    return (Dataset.from_list([{"messages": r["messages"]} for r in train]),
            Dataset.from_list([{"messages": r["messages"]} for r in val_rows]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="unsloth/Qwen3-8B-unsloth-bnb-4bit")
    ap.add_argument("--train", default="corpus/train.jsonl")
    ap.add_argument("--val", default="corpus/val.jsonl")
    ap.add_argument("--out", default="outputs/critic-qwen3-8b")
    ap.add_argument("--upsample", type=int, default=20,
                    help="repeat factor for hudson-forge-original rows")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--lora-rank", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", default=None,
                    help="path to a checkpoint dir to resume from, "
                         "e.g. outputs/critic-qwen3-8b/checkpoint-150")
    args = ap.parse_args()

    # --- Model: load in 4-bit, attach LoRA adapters ------------------------
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.seq_len,
        load_in_4bit=True,
        dtype=None,             # autodetect bf16 on Blackwell
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        lora_alpha=args.lora_rank * 2,          # alpha = 2r is a safe default
        lora_dropout=0.0,                       # 0.0 lets Unsloth use a fast path
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",   # big VRAM saving
        random_state=args.seed,
    )

    tokenizer = get_chat_template(tokenizer, chat_template="qwen3")

    # --- Data --------------------------------------------------------------
    train_ds, val_ds = load_corpus(args.train, args.val, args.upsample)

    def format_chat(batch):
        texts = [tokenizer.apply_chat_template(m, tokenize=False,
                                               add_generation_prompt=False)
                 for m in batch["messages"]]
        return {"text": texts}

    train_ds = train_ds.map(format_chat, batched=True,
                            remove_columns=train_ds.column_names)
    val_ds = val_ds.map(format_chat, batched=True,
                        remove_columns=val_ds.column_names)

    # --- Trainer -----------------------------------------------------------
    cfg = SFTConfig(
        output_dir=args.out,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,         # effective batch = 16
        warmup_ratio=0.03,
        num_train_epochs=args.epochs,
        learning_rate=2e-4,                     # standard LoRA LR
        logging_steps=5,
        optim="adamw_8bit",                     # 8-bit optimizer saves VRAM
        weight_decay=0.01,
        max_grad_norm=1.0,          # clip gradient spikes (saw 3.8e12 earlier)
        lr_scheduler_type="cosine",
        seed=args.seed,
        max_seq_length=args.seq_len,
        dataset_text_field="text",
        packing=False,                          # keep examples separate
        eval_strategy="steps",
        eval_steps=25,
        per_device_eval_batch_size=1,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=3,
        bf16=True,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        args=cfg,
    )

    # Train only on the assistant's tokens, not the prompt. This is what
    # teaches the model to PRODUCE critiques rather than to model the whole
    # transcript including the questions.
    from unsloth.chat_templates import train_on_responses_only
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )

    print("\n=== starting training ===")
    if args.resume:
        print(f"resuming from {args.resume}")
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()

    # --- Save merged adapter ----------------------------------------------
    final = Path(args.out) / "final"
    model.save_pretrained_merged(str(final), tokenizer,
                                 save_method="merged_16bit")
    print(f"\nDone. Merged model at {final}")
    print("Next: run baseline_eval.py before AND after to measure the delta.")


if __name__ == "__main__":
    main()
