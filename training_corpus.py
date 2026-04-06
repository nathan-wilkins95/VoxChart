"""
training_corpus.py
Fine-tune OpenAI Whisper on your own recorded medical dictation samples.
Samples are the .wav/.txt pairs saved by DictationEngine into training_corpus/.

Usage (standalone):
    python training_corpus.py

Or call fine_tune() from app.py in a background thread.
"""
from __future__ import annotations
import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

CORPUS_DIR  = Path("training_corpus")
OUTPUT_DIR  = Path("whisper-medical-finetuned")
BASE_MODEL  = "openai/whisper-small.en"
logger      = logging.getLogger("voxchart.training")


@dataclass
class TrainingConfig:
    corpus_dir:   Path = CORPUS_DIR
    output_dir:   Path = OUTPUT_DIR
    base_model:   str  = BASE_MODEL
    epochs:       int  = 3
    batch_size:   int  = 4
    learning_rate: float = 1e-5
    fp16:         bool = True
    max_samples:  int  = 0   # 0 = use all


def load_corpus(corpus_dir: Path, max_samples: int = 0):
    """Load .wav/.txt pairs from corpus_dir. Returns (audio_paths, texts)."""
    wav_files = sorted(corpus_dir.glob("*.wav"))
    audio_paths, texts = [], []
    for wav in wav_files:
        txt = wav.with_suffix(".txt")
        if not txt.exists():
            continue
        text = txt.read_text(encoding="utf-8").strip()
        if not text:
            continue
        audio_paths.append(str(wav))
        texts.append(text)
        if max_samples and len(audio_paths) >= max_samples:
            break
    logger.info("Loaded %d training pairs from %s", len(audio_paths), corpus_dir)
    return audio_paths, texts


def fine_tune(
    config: TrainingConfig | None = None,
    on_progress: Callable[[str], None] | None = None,
):
    """
    Fine-tune Whisper on the recorded corpus.
    on_progress(msg) is called with status updates (safe to call from thread).
    Raises RuntimeError if corpus is empty or dependencies are missing.
    """
    if config is None:
        config = TrainingConfig()

    def log(msg: str):
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    # -- Dependency check --
    try:
        from datasets import Dataset, Audio
        from transformers import (
            WhisperProcessor,
            WhisperForConditionalGeneration,
            Seq2SeqTrainingArguments,
            Seq2SeqTrainer,
        )
        import torch
    except ImportError as e:
        raise RuntimeError(
            f"Missing dependency: {e}\n"
            "Run: pip install transformers datasets accelerate"
        ) from e

    # -- Load corpus --
    audio_paths, texts = load_corpus(config.corpus_dir, config.max_samples)
    if not audio_paths:
        raise RuntimeError(
            f"No training samples found in {config.corpus_dir}.\n"
            "Dictate some sessions first — each session saves a .wav/.txt pair."
        )

    log(f"Training on {len(audio_paths)} samples with {config.base_model}...")

    # -- Build HuggingFace dataset --
    ds = Dataset.from_dict({"audio": audio_paths, "text": texts})
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    processor = WhisperProcessor.from_pretrained(config.base_model)
    model     = WhisperForConditionalGeneration.from_pretrained(config.base_model)

    def preprocess(examples):
        inputs = processor(
            examples["audio"]["array"],
            sampling_rate=16000,
            return_tensors="pt",
        )
        labels = processor.tokenizer(examples["text"], return_tensors="pt").input_ids
        inputs["labels"] = labels
        return inputs

    log("Preprocessing audio...")
    ds = ds.map(preprocess, batched=False, remove_columns=ds.column_names)

    use_fp16 = config.fp16 and torch.cuda.is_available()
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(config.output_dir),
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=2,
        learning_rate=config.learning_rate,
        num_train_epochs=config.epochs,
        fp16=use_fp16,
        save_strategy="epoch",
        logging_steps=10,
        save_total_limit=2,
        load_best_model_at_end=False,
        report_to="none",
        predict_with_generate=True,
    )

    class ProgressCallback:
        """Relay HuggingFace trainer logs to on_progress."""
        from transformers import TrainerCallback
        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs and on_progress:
                step  = logs.get("step", state.global_step)
                loss  = logs.get("loss", "--")
                on_progress(f"Step {step}  loss={loss}")

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=ds,
        tokenizer=processor.feature_extractor,
    )

    log("Starting training...")
    trainer.train()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    processor.save_pretrained(str(config.output_dir))
    model.save_pretrained(str(config.output_dir))
    log(f"Fine-tuned model saved to {config.output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fine_tune(on_progress=print)
