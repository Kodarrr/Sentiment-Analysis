# ML & Fine-Tuning Pipeline

This directory contains the machine learning pipelines, fine-tuning scripts, and experimentation notebooks for the **Bangla + English Sentiment Engine**.

## Directory Structure

```
ml/
├── notebooks/
│   └── fine_tune_banglabert.ipynb   # Ready-to-run Kaggle / Colab GPU Notebook
├── training/
│   └── train_banglabert.py          # Standalone training Python script
└── data_pipeline/
    └── preprocess.py                # Text normalization and data preparation logic
```

## How to Run on Kaggle (Step-by-Step)

1. Open [Kaggle](https://www.kaggle.com/) and click **Create** > **New Notebook**.
2. Click **File** > **Import Notebook** and upload `ml/notebooks/fine_tune_banglabert.ipynb`.
3. In the right sidebar:
   - **Data**: Click **Add Input** and select/upload your Kaggle Sentiment CSV dataset.
   - **Settings** > **Accelerator**: Select **GPU T4 x2** (or GPU P100).
   - **Settings** > **Internet**: Turn **ON** (needed to download `csebuetnlp/banglabert` weights).
4. Run all cells (`Shift + Enter` or `Run All`).
5. After training completes (takes ~5-8 minutes on T4):
   - You can download `bangla_sentiment_model.zip` directly from the Kaggle **Output** section.
   - OR use Step 10 in the notebook to push it directly to your Hugging Face Hub account.

