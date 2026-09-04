import pandas as pd
import joblib
from datetime import datetime

df = pd.read_csv("holdout_flows.csv").sort_values("ts").reset_index(drop=True)

COMMON_PORTS = {
    80: "http", 443: "https", 22: "ssh", 21: "ftp",
    5201: "iperf3_test", 5202: "iperf3_test", 5203: "iperf3_test", 5300: "iperf3_test",
    8080: "http_alt", 8090: "http_alt", 53: "dns"
}

df["orig_bytes"] = df["orig_bytes"].fillna(0)
df["resp_bytes"] = df["resp_bytes"].fillna(0)
df["duration"] = df["duration"].fillna(0)

df["byte_ratio"] = df["orig_bytes"] / (df["resp_bytes"] + 1)
df["port_category"] = df["id.resp_p"].apply(lambda p: COMMON_PORTS.get(p, "unusual"))
df["is_unusual_port"] = df["port_category"] == "unusual"
df["hour_of_day"] = df["ts"].apply(lambda t: datetime.fromtimestamp(t).hour)
df["bytes_per_second"] = df["orig_bytes"] / df["duration"].replace(0, 0.001)
df["is_burst"] = (df["duration"] < 2) & (df["orig_bytes"] > 10000)

# Fresh channel history -- this is holdout data, must NOT reuse training channel counts
channel_counts = {}
new_channel_flags = []
for _, row in df.iterrows():
    key = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    channel_counts[key] = channel_counts.get(key, 0) + 1
    new_channel_flags.append(channel_counts[key] == 1)
df["new_channel"] = new_channel_flags

# ---- Load the ALREADY-TRAINED model -- no retraining ----
model = joblib.load("trained_model.joblib")
FEATURE_COLS = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]

X = df[FEATURE_COLS].fillna(0).copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

df["if_anomaly"] = model.predict(X) == -1

# ---- Same trickle rule, same threshold (>=5), applied fresh to holdout channel counts ----
def final_key_count(row):
    key = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    return channel_counts[key]

df["channel_total_flows"] = df.apply(final_key_count, axis=1)
df["trickle_anomaly"] = df["channel_total_flows"] >= 5

def combined_alert(row):
    reasons, confidence = [], 0.0
    if row["if_anomaly"]:
        reasons.append("per-flow statistical anomaly (Isolation Forest)")
        confidence += 0.5
    if row["trickle_anomaly"]:
        reasons.append("repeated low-volume channel to new destination")
        confidence += 0.6
    if row["is_unusual_port"] and row["byte_ratio"] > 100:
        reasons.append("unusual port with high outbound/inbound byte ratio")
        confidence += 0.2
    confidence = min(confidence, 1.0)
    return pd.Series({"alert_confidence": round(confidence, 2), "is_alert": confidence > 0})

df[["alert_confidence", "is_alert"]] = df.apply(combined_alert, axis=1)

print("=== HOLDOUT results (unseen traffic, unchanged model + threshold) ===")
print(df.groupby(["label", "is_alert"]).size())

print("\n=== Detail ===")
print(df[["id.orig_h","id.resp_h","id.resp_p","orig_bytes","duration","if_anomaly","trickle_anomaly","alert_confidence","is_alert","label"]].to_string(index=False))

df.to_csv("holdout_results.csv", index=False)
