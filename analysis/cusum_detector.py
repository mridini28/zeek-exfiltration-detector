import pandas as pd
import numpy as np

df = pd.read_csv("features.csv")
df = df.sort_values("ts").reset_index(drop=True)

WINDOW_SECONDS = 60  # rolling window size

print("=== Per (source, destination) windowed outbound volume ===\n")

for (src, dst), group in df.groupby(["id.orig_h", "id.resp_h"]):
    group = group.sort_values("ts").reset_index(drop=True)
    t0 = group["ts"].iloc[0]
    group["window"] = ((group["ts"] - t0) // WINDOW_SECONDS).astype(int)

    windowed = group.groupby("window").agg(
        total_outbound=("orig_bytes", "sum"),
        num_flows=("orig_bytes", "count"),
        labels=("label", lambda x: x.unique().tolist())
    ).reset_index()

    print(f"Source: {src} -> Destination: {dst}")
    print(windowed.to_string(index=False))
    print()

    # Simple CUSUM: flag when a window's outbound volume deviates significantly
    # from that source-dest pair's own historical mean+std
    mean = windowed["total_outbound"].mean()
    std = windowed["total_outbound"].std(ddof=0)
    if std > 0:
        windowed["zscore"] = (windowed["total_outbound"] - mean) / std
        flagged = windowed[windowed["zscore"].abs() > 1.5]
        if not flagged.empty:
            print(f"  --> Flagged windows (|z| > 1.5):\n{flagged.to_string(index=False)}\n")
