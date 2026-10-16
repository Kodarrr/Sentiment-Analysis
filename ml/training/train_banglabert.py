"""
BanglaBERT Fine-Tuning Script for Sentiment Analysis.

Designed for execution on Kaggle / Google Colab (GPU accelerated: T4 / P100).
Trains a sequence classification head on top of 'csebuetnlp/banglabert'.
Supports:
- Robust CSV loading & cleaning
- Train/Validation/Test splitting
- Mixed precision (fp16) training with HuggingFace Trainer
- Accuracy, Precision, Recall, Macro-F1 evaluation
- Saving model weights and tokenizer locally and optionally pushing to Hugging Face Hub.
"""

import os
import re
import numpy as np
import pandas as pd
import torch
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_MODEL_NAME = "csebuetnlp/banglabert"
OUTPUT_DIR = "./bangla_sentiment_model"
LOGS_DIR = "./training_logs"

# Adjust these to match your dataset
CSV_PATH = "ml/large_sentiment_analysis_dataset.csv"  # e.g., "large_sentiment_analysis_dataset.csv"
TEXT_COLUMN = "Comment"                                # Column containing Bengali text
LABEL_COLUMN = "Sentiment"                            # Column containing sentiment labels

# Training hyperparameters
BATCH_SIZE = 16
MAX_LENGTH = 128
LEARNING_RATE = 2e-5
EPOCHS = 3
WEIGHT_DECAY = 0.01
SEED = 42

# Optional: Push to Hugging Face Hub (Set token if you want to auto-upload)
HF_TOKEN = ""                  # e.g., "hf_xxxxxxxxxxxxx"
HF_REPO_NAME = ""              # e.g., "username/bangla-sentiment-bert"


# ==========================================
# 2. TEXT CLEANING & PREPROCESSING
# ==========================================
def clean_bangla_text(text: str) -> str:
    """Basic normalization for Bengali text."""
    if not isinstance(text, str):
        return ""
    # Normalize whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    # Remove HTML tags if present
    text = re.sub(r"<[^>]+>", "", text)
    # Remove excessive punctuation repetitions (e.g., !!!!! -> !)
    text = re.sub(r"([!?.।])\1+", r"\1", text)
    return text


def prepare_dataset(csv_path: str, text_col: str, label_col: str) -> tuple[DatasetDict, dict, dict]:
    print(f"[*] Loading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Validate columns
    if text_col not in df.columns or label_col not in df.columns:
        raise ValueError(
            f"Columns not found! Available columns: {list(df.columns)}. "
            f"Expected '{text_col}' and '{label_col}'."
        )

    # Drop NaNs
    df = df.dropna(subset=[text_col, label_col]).copy()
    df[text_col] = df[text_col].astype(str).apply(clean_bangla_text)
    df = df[df[text_col].str.len() > 2]  # Remove empty/too short strings

    # Standardize labels
    # If labels are strings like 'positive'/'negative' or 'pos'/'neg'
    unique_labels = sorted(list(df[label_col].unique()))
    print(f"[*] Found labels in dataset: {unique_labels}")

    # Create mapping: standardizing to NEGATIVE (0), POSITIVE (1)
    label2id = {}
    id2label = {}

    if set(unique_labels) == {0, 1}:
        id2label = {0: "NEGATIVE", 1: "POSITIVE"}
        label2id = {"NEGATIVE": 0, "POSITIVE": 1}
        df["target"] = df[label_col].astype(int)
    else:
        # String mapping
        for idx, lbl in enumerate(unique_labels):
            str_lbl = str(lbl).strip().upper()
            if "POS" in str_lbl or str_lbl == "1":
                mapped_name = "POSITIVE"
                target_id = 1
            elif "NEG" in str_lbl or str_lbl == "0":
                mapped_name = "NEGATIVE"
                target_id = 0
            else:
                mapped_name = str_lbl
                target_id = idx

            label2id[mapped_name] = target_id
            id2label[target_id] = mapped_name

        # Map to integer target column
        # Handle cases where label is raw string
        def map_val(v):
            str_v = str(v).strip().upper()
            if "POS" in str_v or str_v == "1":
                return 1
            return 0

        df["target"] = df[label_col].apply(map_val)
        id2label = {0: "NEGATIVE", 1: "POSITIVE"}
        label2id = {"NEGATIVE": 0, "POSITIVE": 1}

    print(f"[*] Label distribution:\n{df['target'].value_counts()}")

    # Stratified Train / Validation / Test split (80% / 10% / 10%)
    train_df, test_df = train_test_split(
        df[[text_col, "target"]],
        test_size=0.2,
        random_state=SEED,
        stratify=df["target"]
    )
    val_df, test_df = train_test_split(
        test_df,
        test_size=0.5,
        random_state=SEED,
        stratify=test_df["target"]
    )

    print(f"[*] Split sizes - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    dataset_dict = DatasetDict({
        "train": Dataset.from_pandas(train_df.rename(columns={text_col: "text", "target": "label"})),
        "validation": Dataset.from_pandas(val_df.rename(columns={text_col: "text", "target": "label"})),
        "test": Dataset.from_pandas(test_df.rename(columns={text_col: "text", "target": "label"})),
    })

    return dataset_dict, id2label, label2id


# ==========================================
# 3. METRICS EVALUATION
# ==========================================
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="macro", zero_division=0
    )
    acc = accuracy_score(labels, preds)
    return {
        "accuracy": float(acc),
        "f1": float(f1),
        "precision": float(precision),
        "recall": float(recall),
    }


# ==========================================
# 4. MAIN TRAINING PIPELINE
# ==========================================
def run_training():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Using compute device: {device}")
    if device == "cuda":
        print(f"[*] GPU Model: {torch.cuda.get_device_name(0)}")

    # Prepare data
    datasets, id2label, label2id = prepare_dataset(CSV_PATH, TEXT_COLUMN, LABEL_COLUMN)

    # Load Tokenizer
    print(f"[*] Loading tokenizer for: {BASE_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

    def tokenize_fn(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=MAX_LENGTH
        )

    print("[*] Tokenizing dataset...")
    tokenized_datasets = datasets.map(tokenize_fn, batched=True)

    # Load Model
    print(f"[*] Loading base model: {BASE_MODEL_NAME}")
    num_labels = len(id2label)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL_NAME,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # Training Arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=EPOCHS,
        weight_decay=WEIGHT_DECAY,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_dir=LOGS_DIR,
        logging_steps=50,
        fp16=torch.cuda.is_available(),  # Fast training on GPU
        seed=SEED,
        report_to="none"  # Can change to "tensorboard" or "wandb"
    )

    # Compatible with both modern (>=4.46) and older transformers versions
    import inspect
    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": tokenized_datasets["train"],
        "eval_dataset": tokenized_datasets["validation"],
        "data_collator": data_collator,
        "compute_metrics": compute_metrics,
    }
    if "processing_class" in inspect.signature(Trainer.__init__).parameters:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    print("[*] Starting training...")
    trainer.train()

    print("[*] Evaluating on held-out test set...")
    test_metrics = trainer.evaluate(tokenized_datasets["test"])
    print(f"[*] Test Set Results: {test_metrics}")

    # Save final best model & tokenizer
    print(f"[*] Saving best model and tokenizer to: {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Optional: Push to Hugging Face Hub
    if HF_TOKEN and HF_REPO_NAME:
        print(f"[*] Pushing to Hugging Face Hub: {HF_REPO_NAME}...")
        model.push_to_hub(HF_REPO_NAME, token=HF_TOKEN)
        tokenizer.push_to_hub(HF_REPO_NAME, token=HF_TOKEN)
        print("[*] Successfully pushed to Hugging Face Hub!")

    print("[*] Pipeline complete!")


if __name__ == "__main__":
    run_training()

