import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

df = pd.read_csv("features_v2.csv")

# ---- Select numeric features for the model ----
# These should be things that generalize across any traffic, not IP/port identifiers themselves
feature_cols = [
    "orig_bytes", "resp_bytes", "byte_ratio", "duration",
    "bytes_per_second", "hour_of_day"
]

X = df[feature_cols].fillna(0)

# Boolean columns need to become 0/1
X = X.copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

# ---- Train ONLY on benign data ----
train_mask = df["label"] == "benign"
X_train = X[train_mask]

print(f"Training on {len(X_train)} benign flows")
print(f"Scoring {len(X)} total flows\n")

model = IsolationForest(
    n_estimators=100,
    contamination=0.1,   # expected proportion of anomalies — tune later
    random_state=42
)
model.fit(X_train)

# ---- Score everything ----
df["anomaly_score"] = model.decision_function(X)  # higher = more normal
df["is_anomaly"] = model.predict(X) == -1          # -1 = anomaly, 1 = normal

print("=== Isolation Forest results ===")
cols = ["id.orig_h", "id.resp_h", "id.resp_p", "orig_bytes", "byte_ratio",
        "duration", "anomaly_score", "is_anomaly", "label"]
print(df[cols].sort_values("anomaly_score").to_string(index=False))

print("\n=== Accuracy check (informal, tiny dataset) ===")
print(df.groupby(["label", "is_anomaly"]).size())

df.to_csv("isolation_forest_results.csv", index=False)
print("\nSaved to isolation_forest_results.csv")
