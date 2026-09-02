import pandas as pd
from sklearn.ensemble import IsolationForest
from host_baseline import HostBaseline

df = pd.read_csv("features_v3.csv").sort_values("ts").reset_index(drop=True)

# ---- Layer 1: Isolation Forest (per-flow anomaly) ----
feature_cols = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]
X = df[feature_cols].fillna(0).copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

train_mask = df["label"] == "benign"
model = IsolationForest(n_estimators=200, contamination=0.15, random_state=42)
model.fit(X[train_mask])

df["if_score"] = model.decision_function(X)          # higher = more normal
df["if_anomaly"] = model.predict(X) == -1

# ---- Layer 2: HostBaseline (channel repetition / trickle detection) ----
baseline = HostBaseline(window_seconds=60, zscore_threshold=1.5)
for _, row in df.iterrows():
    baseline.update(row["id.orig_h"], row["id.resp_h"], row["id.resp_p"], row["ts"], row["orig_bytes"])

channel_flow_counts = {}
for key, history in baseline.channel_history.items():
    channel_flow_counts[key] = len(history)

def trickle_flag(row):
    key = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    return channel_flow_counts.get(key, 0) >= 5   # same threshold as before: repeated small transfers

df["trickle_anomaly"] = df.apply(trickle_flag, axis=1)

# ---- Combine into final alert ----
def combined_alert(row):
    reasons = []
    confidence = 0.0

    if row["if_anomaly"]:
        reasons.append("per-flow statistical anomaly (Isolation Forest)")
        confidence += 0.5

    if row["trickle_anomaly"]:
        reasons.append("repeated low-volume channel to new destination (possible slow exfiltration)")
        confidence += 0.6

    if row["is_unusual_port"] and row["byte_ratio"] > 100:
        reasons.append("unusual port with high outbound/inbound byte ratio")
        confidence += 0.2

    confidence = min(confidence, 1.0)
    is_alert = confidence > 0.0
    return pd.Series({"alert_confidence": round(confidence, 2), "alert_reasons": "; ".join(reasons), "is_alert": is_alert})

df[["alert_confidence", "alert_reasons", "is_alert"]] = df.apply(combined_alert, axis=1)

# ---- Output in the alert schema shape ----
alerts = df[df["is_alert"]].copy()
alerts["threat_class"] = "data_exfiltration"
alert_schema = alerts[["ts", "uid", "id.orig_h", "id.resp_h", "id.resp_p", "threat_class", "alert_confidence", "alert_reasons", "label"]]
alert_schema = alert_schema.rename(columns={"uid": "flow_id", "ts": "timestamp"})

print("=== Final combined alerts ===")
print(alert_schema.to_string(index=False))

print("\n=== Detection summary vs ground truth ===")
print(df.groupby(["label", "is_alert"]).size())

df.to_csv("combined_detector_results.csv", index=False)
alert_schema.to_csv("alerts.csv", index=False)
print("\nSaved combined_detector_results.csv and alerts.csv")
