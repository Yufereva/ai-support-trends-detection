"""Transparent baseline clustering for support ticket text."""

from __future__ import annotations

import math
import os

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from support_trend_detection.config import RANDOM_STATE

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


def choose_cluster_count(ticket_count: int) -> int:
    if ticket_count < 12:
        return max(1, min(ticket_count, 3))
    return max(4, min(10, round(math.sqrt(ticket_count / 3))))


def assign_clusters(tickets: pd.DataFrame, cluster_count: int | None = None) -> pd.DataFrame:
    clustered = tickets.copy()
    if clustered.empty:
        clustered["cluster_id"] = []
        return clustered

    n_clusters = cluster_count or choose_cluster_count(len(clustered))
    n_clusters = max(1, min(n_clusters, len(clustered)))

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    matrix = vectorizer.fit_transform(clustered["analysis_text"])

    if n_clusters == 1:
        labels = [0] * len(clustered)
    else:
        model = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
        labels = model.fit_predict(matrix)

    clustered["cluster_id"] = [f"cluster-{label}" for label in labels]
    return clustered


def top_terms_for_cluster(tickets: pd.DataFrame, top_n: int = 5) -> dict[str, list[str]]:
    if tickets.empty:
        return {}

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    matrix = vectorizer.fit_transform(tickets["analysis_text"])
    terms = vectorizer.get_feature_names_out()
    output: dict[str, list[str]] = {}

    for cluster_id, group in tickets.groupby("cluster_id"):
        indices = group.index.to_list()
        scores = matrix[indices].mean(axis=0).A1
        ranked = scores.argsort()[::-1]
        output[cluster_id] = [terms[i] for i in ranked[:top_n] if scores[i] > 0]

    return output
