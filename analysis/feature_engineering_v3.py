import pandas as pd
import numpy as np
from datetime import datetime

df = pd.read_csv("combined_flows_v2.csv")
df = df.sort_values("ts").reset_index(drop=True)

COMMON_PORTS = {
    80: "http", 443: "https", 22: "ssh", 21: "ftp",
    5201: "iperf3_test", 5202: "iperf3_test", 5203: "iperf3_test",
    8080: "http_alt", 53: "dns"
}

def classify_port(port):
    return COMMON_PORTS.get(port, "unusual")

df["byte_ratio"] = df["orig_bytes"] / (df["resp_bytes"] + 1)
df["port_category"] = df["id.resp_p"].apply(classify_port)
df["is_unusual_port"] = df["port_category"] == "unusual"
df["hour_of_day"] = df["ts"].apply(lambda t: datetime.fromtimestamp(t).hour)
df["bytes_per_second"] = df["orig_bytes"] / df["duration"].replace(0, 0.001)
df["is_burst"] = (df["duration"] < 2) & (df["orig_bytes"] > 10000)

seen_channels = set()
novelty_flags = []
for _, row in df.iterrows():
    channel = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    novelty_flags.append(channel not in seen_channels)
    seen_channels.add(channel)
df["new_channel"] = novelty_flags

df.to_csv("features_v3.csv", index=False)
print(f"Saved {len(df)} rows to features_v3.csv")
print(df[["id.resp_p","port_category","orig_bytes","byte_ratio","duration","is_burst","is_unusual_port","label"]].to_string(index=False))
