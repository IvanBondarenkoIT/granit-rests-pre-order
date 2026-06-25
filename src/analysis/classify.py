"""Классификация спроса по Syntetos-Boylan (ADI, CV^2) для выбора метода прогноза."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Пороги Syntetos-Boylan
ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49


@dataclass(frozen=True)
class DemandClass:
    label: str          # smooth | intermittent | erratic | lumpy | new
    adi: float
    cv2: float
    nonzero_periods: int


def classify(demand: pd.Series) -> DemandClass:
    """demand — недельный ряд (true_demand). Возвращает класс спроса."""
    d = pd.to_numeric(demand, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    n = len(d)
    nz = d[d > 0]
    if n == 0 or len(nz) < 2:
        return DemandClass("new", float("inf"), 0.0, int(len(nz)))
    adi = n / len(nz)
    mean_nz = nz.mean()
    cv2 = float((nz.std(ddof=0) / mean_nz) ** 2) if mean_nz > 0 else 0.0
    if adi < ADI_THRESHOLD and cv2 < CV2_THRESHOLD:
        label = "smooth"
    elif adi >= ADI_THRESHOLD and cv2 < CV2_THRESHOLD:
        label = "intermittent"
    elif adi < ADI_THRESHOLD and cv2 >= CV2_THRESHOLD:
        label = "erratic"
    else:
        label = "lumpy"
    return DemandClass(label, round(adi, 3), round(cv2, 3), int(len(nz)))
