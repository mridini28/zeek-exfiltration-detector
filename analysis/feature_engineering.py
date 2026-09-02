import pandas as pd
import numpy as np

df = pd.read_csv("combined_flows.csv")
df = df.sort_values("ts").reset_index(drop=True)

# ---- Per-flow features ----
# Outbound/inbound byte ratio (avoid divide-by-zero)
df["byte_ratio"] = df["orig_bytes"] / (df["resp_bytes"] + 1)

# Destination novelty: has this source talked to this destination before?
seen_pairs = set()
novelty_flags = []
for _, row in df.iterrows():
    pair = (row["id.orig_h"], row["id.resp_h"])
    novelty_flags.append(pair not in seen_pairs)
    seen_pairs.add(pair)
df["new_destination"] = novelty_flags

print("=== Per-flow features ===")
print(df[["ts", "id.orig_h", "id.resp_h", "id.resp_p", "orig_bytes", "resp_bytes", "byte_ratio", "duration", "new_destination", "label"]].to_string(index=False))

# ---- Per-source rolling aggregation (CUSUM-style) ----
print("\n=== Per-source cumulative outbound bytes over time (CUSUM input) ===")
for source in df["id.orig_h"].unique():
    sub = df[df["id.orig_h"] == source].copy()
    sub["cumulative_outbound"] = sub["orig_bytes"].cumsum()
    print(f"\nSource: {source}")
    print(sub[["ts", "id.resp_h", "id.resp_p", "orig_bytes", "cumulative_outbound", "label"]].to_string(index=False))

df.to_csv("features.csv", index=False)
print("\nSaved to features.csv")
