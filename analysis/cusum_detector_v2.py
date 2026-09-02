import pandas as pd
import numpy as np

df = pd.read_csv("features.csv")
df = df.sort_values("ts").reset_index(drop=True)

WINDOW_SECONDS = 60

print("=== Per (source, destination, port) windowed outbound volume ===\n")

for (src, dst, port), group in df.groupby(["id.orig_h", "id.resp_h", "id.resp_p"]):
    group = group.sort_values("ts").reset_index(drop=True)
    t0 = group["ts"].iloc[0]
    group["window"] = ((group["ts"] - t0) // WINDOW_SECONDS).astype(int)

    windowed = group.groupby("window").agg(
        total_outbound=("orig_bytes", "sum"),
        num_flows=("orig_bytes", "count"),
        labels=("label", lambda x: x.unique().tolist())
    ).reset_index()

    print(f"Source: {src} -> Destination: {dst}:{port}")
    print(windowed.to_string(index=False))
    print()

# ---- Now look specifically at the slow-trickle channel across its full duration ----
print("\n=== Cumulative outbound on port 9998 (the trickle channel) over its own timeline ===")
trickle = df[df["id.resp_p"] == 9998].copy().sort_values("ts").reset_index(drop=True)
trickle["cumulative_outbound"] = trickle["orig_bytes"].cumsum()
trickle["seconds_since_start"] = trickle["ts"] - trickle["ts"].iloc[0]
print(trickle[["seconds_since_start", "orig_bytes", "cumulative_outbound"]].to_string(index=False))
