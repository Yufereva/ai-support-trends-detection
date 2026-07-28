#!/usr/bin/env python3
"""Evaluate semantic retrieval and time-window trend alerts on dataset v2."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "full_dataset.json"
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLDS = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75)
WINDOW = timedelta(days=7)
MIN_PREVIOUS_MATCHES = 3
PRODUCTION_THRESHOLD = 0.60


def metrics(expected: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float, int]:
    true_positive = int(np.sum(expected & predicted))
    false_positive = int(np.sum(~expected & predicted))
    false_negative = int(np.sum(expected & ~predicted))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, false_positive


def main() -> None:
    tickets = json.loads(DATA_PATH.read_text(encoding="utf-8"))["tickets"]
    texts = [f"{ticket['subject']} {ticket['body']}" for ticket in tickets]
    topics = [ticket["ground_truth"]["topic_id"] for ticket in tickets]
    categories = [ticket["category"] for ticket in tickets]
    emerging = np.array([ticket["ground_truth"]["is_emerging_trend"] for ticket in tickets])
    created = [datetime.fromisoformat(ticket["created_at"]) for ticket in tickets]

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    scores = embeddings @ embeddings.T
    np.fill_diagonal(scores, -1)
    nearest_topic_accuracy = np.mean([topics[int(scores[i].argmax())] == topics[i] for i in range(len(tickets))])

    previous_in_window: list[list[int]] = []
    expected = np.zeros(len(tickets), dtype=bool)
    for index, ticket_time in enumerate(created):
        previous = [candidate for candidate in range(index) if ticket_time - WINDOW <= created[candidate] < ticket_time]
        previous_in_window.append(previous)
        same_topic = sum(topics[candidate] == topics[index] for candidate in previous)
        expected[index] = bool(emerging[index] and same_topic >= MIN_PREVIOUS_MATCHES)

    print(f"Tickets: {len(tickets)}")
    print(f"Nearest-neighbor topic accuracy: {nearest_topic_accuracy:.1%}")
    print(f"Expected alert-positive tickets: {int(expected.sum())}")
    print(f"Rule: >= {MIN_PREVIOUS_MATCHES} earlier similar tickets in {WINDOW.days} days")
    print("Threshold calibration:")
    production_predicted = None
    production_counts = None
    for threshold in THRESHOLDS:
        match_counts = np.array([
            sum(
                scores[index, candidate] >= threshold and categories[candidate] == categories[index]
                for candidate in previous_in_window[index]
            ) >= MIN_PREVIOUS_MATCHES
            for index in range(len(tickets))
        ])
        predicted = match_counts
        precision, recall, f1, false_positive = metrics(expected, predicted)
        print(
            f"  {threshold:.2f}: precision={precision:.1%}, recall={recall:.1%}, "
            f"F1={f1:.1%}, false_positives={false_positive}"
        )
        if threshold == PRODUCTION_THRESHOLD:
            production_predicted = predicted
            production_counts = np.array([
                sum(
                    scores[index, candidate] >= threshold and categories[candidate] == categories[index]
                    for candidate in previous_in_window[index]
                )
                for index in range(len(tickets))
            ])

    false_positive_indices = np.where(~expected & production_predicted)[0]
    print("Production-threshold false positives:")
    for index in false_positive_indices:
        matching = [
            candidate for candidate in previous_in_window[index]
            if scores[index, candidate] >= PRODUCTION_THRESHOLD
            and categories[candidate] == categories[index]
        ]
        evidence = ", ".join(
            f"{tickets[candidate]['id']}={scores[index, candidate]:.1%}"
            for candidate in sorted(matching, key=lambda candidate: scores[index, candidate], reverse=True)
        )
        print(
            f"  {tickets[index]['id']} topic={topics[index]} "
            f"matches={len(matching)} [{evidence}]"
        )

    boundary_indices = np.where((~production_predicted) & (production_counts == MIN_PREVIOUS_MATCHES - 1))[0]
    if boundary_indices.size:
        index = int(boundary_indices[-1])
        matching = [
            candidate for candidate in previous_in_window[index]
            if scores[index, candidate] >= PRODUCTION_THRESHOLD
            and categories[candidate] == categories[index]
        ]
        evidence = ", ".join(
            f"{tickets[candidate]['id']}={scores[index, candidate]:.1%}"
            for candidate in sorted(matching, key=lambda candidate: scores[index, candidate], reverse=True)
        )
        print(
            f"Boundary below alert: {tickets[index]['id']} topic={topics[index]} "
            f"matches={len(matching)}/{MIN_PREVIOUS_MATCHES} [{evidence}]"
        )


if __name__ == "__main__":
    main()
