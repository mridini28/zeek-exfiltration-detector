import pandas as pd
import numpy as np
from datetime import datetime

df = pd.read_csv("combined_flows.csv")
df = df.sort_values("ts").reset_index(drop=True)

# ---- Known "normal" ports for bulk/interactive traffic ----
# Extend this as you add more benign traffic types
COMMON_PORTS = {
    80: "http", 443: "https", 22: "ssh", 21: "ftp",
    5201: "iperf3_test", 8080: "http_alt", 53: "dns"
}

def classify_port(port):
    return COMMON_PORTS.get(port, "unusual")

# ---- Per-flow features ----
df["byte_ratio"] = df["orig_bytes"] / (df["resp_bytes"] + 1)
df["port_category"] = df["id.resp_p"].apply(classify_port)
df["is_unusual_port"] = df["port_category"] == "unusual"

# time of day (hour, 0-23) from unix timestamp
df["hour_of_day"] = df["ts"].apply(lambda t: datetime.fromtimestamp(t).hour)

# burst vs spread classification: short duration + high byte rate = burst
df["bytes_per_second"] = df["orig_bytes"] / df["duration"].replace(0, 0.001)
df["is_burst"] = (df["duration"] < 2) & (df["orig_bytes"] > 10000)

# destination novelty: has this (source, dest, port) combo been seen before this point in time?
seen_channels = set()
novelty_flags = []
for _, row in df.iterrows():
    channel = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    novelty_flags.append(channel not in seen_channels)
    seen_channels.add(channel)
df["new_channel"] = novelty_flags

print("=== Formal per-flow features ===")
cols = ["ts", "id.orig_h", "id.resp_h", "id.resp_p", "port_category",
        "orig_bytes", "resp_bytes", "byte_ratio", "duration",
        "hour_of_day", "is_burst", "is_unusual_port", "new_channel", "label"]
print(df[cols].to_string(index=False))

df.to_csv("features_v2.csv", index=False)
print("\nSaved to features_v2.csv")
