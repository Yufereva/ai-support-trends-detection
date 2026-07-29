#!/usr/bin/env python3
"""Measure whether embeddings recover the curated ground-truth clusters."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "golden_sample.json"
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLDS = (0.50, 0.60, 0.65, 0.70, 0.75)


def main() -> None:
    tickets = json.loads(DATA_PATH.read_text(encoding="utf-8"))["tickets"]
    texts = [f"{item['subject']} {item['body']}" for item in tickets]
    labels = [item["ground_truth"]["cluster_id"] for item in tickets]

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    scores = embeddings @ embeddings.T
    np.fill_diagonal(scores, -1)

    clustered = [index for index, label in enumerate(labels) if label is not None]
    nearest_correct = sum(
        labels[int(scores[index].argmax())] == labels[index] for index in clustered
    )

    same_pairs = []
    different_pairs = []
    for position, left in enumerate(clustered):
        for right in clustered[position + 1 :]:
            target = same_pairs if labels[left] == labels[right] else different_pairs
            target.append(float(scores[left, right]))

    print(f"Nearest-neighbor cluster accuracy: {nearest_correct}/{len(clustered)}")
    print(f"Mean same-cluster cosine: {np.mean(same_pairs):.3f}")
    print(f"Mean cross-cluster cosine: {np.mean(different_pairs):.3f}")
    print("Threshold calibration:")
    for threshold in THRESHOLDS:
        recall = sum(score >= threshold for score in same_pairs) / len(same_pairs)
        false_positive_rate = (
            sum(score >= threshold for score in different_pairs) / len(different_pairs)
        )
        print(
            f"  {threshold:.2f}: same-cluster pair recall={recall:.0%}, "
            f"cross-cluster false-positive rate={false_positive_rate:.0%}"
        )


if __name__ == "__main__":
    main()
