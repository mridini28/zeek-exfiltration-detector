import pandas as pd
from sklearn.ensemble import IsolationForest

df = pd.read_csv("features_v3.csv")

feature_cols = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]
X = df[feature_cols].fillna(0).copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

train_mask = df["label"] == "benign"
X_train = X[train_mask]
print(f"Training on {len(X_train)} benign flows, scoring {len(X)} total\n")

model = IsolationForest(n_estimators=200, contamination=0.15, random_state=42)
model.fit(X_train)

df["anomaly_score"] = model.decision_function(X)
df["is_anomaly"] = model.predict(X) == -1

print(df[["id.orig_h","id.resp_h","id.resp_p","orig_bytes","byte_ratio","duration","anomaly_score","is_anomaly","label"]].sort_values("anomaly_score").to_string(index=False))
print("\n=== Confusion-style breakdown ===")
print(df.groupby(["label","is_anomaly"]).size())

df.to_csv("isolation_forest_results_v2.csv", index=False)
