import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("data/conditionMonitoringOfHydraulicSystems")

SENSORS = [
    "PS1","PS2","PS3","PS4","PS5","PS6",
    "TS1","TS2","TS3","TS4",
    "FS1","FS2","VS1","EPS1"
]

def read_matrix(sensor: str) -> np.ndarray:
    p = BASE / f"{sensor}.txt"
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    # Each line = one cycle/sample. Values are whitespace-separated.
    return np.loadtxt(p)

def row_features(x: np.ndarray, prefix: str) -> pd.DataFrame:
    # x shape: (n_samples, n_points)
    return pd.DataFrame({
        f"{prefix}_mean": x.mean(axis=1),
        f"{prefix}_std":  x.std(axis=1),
        f"{prefix}_min":  x.min(axis=1),
        f"{prefix}_max":  x.max(axis=1),
        f"{prefix}_rms":  np.sqrt((x**2).mean(axis=1)),
    })

frames = []
n_rows = None

for s in SENSORS:
    x = read_matrix(s)
    if x.ndim == 1:
        
        x = x.reshape(-1, 1)

    if n_rows is None:
        n_rows = x.shape[0]
    elif x.shape[0] != n_rows:
        raise ValueError(f"Row count mismatch: {s} has {x.shape[0]} rows, expected {n_rows}")

    frames.append(row_features(x, s))

final = pd.concat(frames, axis=1)
final.insert(0, "sample_id", np.arange(len(final)))

out = Path("data/hydraulic_features.csv")
out.parent.mkdir(parents=True, exist_ok=True)
final.to_csv(out, index=False)

print(f"✅ Wrote {out} with shape {final.shape}")
