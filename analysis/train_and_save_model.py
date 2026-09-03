import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

df = pd.read_csv("features_v3.csv")

feature_cols = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]
X = df[feature_cols].fillna(0).copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

train_mask = df["label"] == "benign"
model = IsolationForest(n_estimators=200, contamination=0.15, random_state=42)
model.fit(X[train_mask])

joblib.dump(model, "trained_model.joblib")
print("Model saved to trained_model.joblib")
