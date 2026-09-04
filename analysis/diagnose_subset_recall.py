import pandas as pd
import joblib

usecols = ["Dst Port", "Flow Duration", "TotLen Fwd Pkts", "TotLen Bwd Pkts", "Label"]
df = pd.read_csv("../real_data/Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv", usecols=usecols, low_memory=False)
df = df[df["Label"] == "Infilteration"].copy()

df["Flow Duration"] = pd.to_numeric(df["Flow Duration"], errors="coerce").fillna(0) / 1_000_000
df["TotLen Fwd Pkts"] = pd.to_numeric(df["TotLen Fwd Pkts"], errors="coerce").fillna(0)
df["TotLen Bwd Pkts"] = pd.to_numeric(df["TotLen Bwd Pkts"], errors="coerce").fillna(0)
df["Dst Port"] = pd.to_numeric(df["Dst Port"], errors="coerce").fillna(0).astype(int)
df["byte_ratio"] = df["TotLen Fwd Pkts"] / (df["TotLen Bwd Pkts"] + 1)

exfil_shaped = df[(df["byte_ratio"] > 10) & (df["TotLen Fwd Pkts"] > 10000)].copy()

COMMON_PORTS = {80, 443, 22, 21, 53}
exfil_shaped["orig_bytes"] = exfil_shaped["TotLen Fwd Pkts"]
exfil_shaped["resp_bytes"] = exfil_shaped["TotLen Bwd Pkts"]
exfil_shaped["duration"] = exfil_shaped["Flow Duration"]
exfil_shaped["is_unusual_port"] = ~exfil_shaped["Dst Port"].isin(COMMON_PORTS)
exfil_shaped["bytes_per_second"] = exfil_shaped["orig_bytes"] / exfil_shaped["duration"].replace(0, 0.001)
exfil_shaped["is_burst"] = (exfil_shaped["duration"] < 2) & (exfil_shaped["orig_bytes"] > 10000)
exfil_shaped["hour_of_day"] = 12
exfil_shaped["new_channel"] = 0

model = joblib.load("trained_model.joblib")
FEATURE_COLS = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]
X = exfil_shaped[FEATURE_COLS].copy()
X["is_burst"] = exfil_shaped["is_burst"].astype(int)
X["is_unusual_port"] = exfil_shaped["is_unusual_port"].astype(int)
X["new_channel"] = exfil_shaped["new_channel"].astype(int)

exfil_shaped["if_anomaly"] = model.predict(X) == -1
caught = exfil_shaped["if_anomaly"].sum()
print(f"Of the {len(exfil_shaped)} real infiltration flows that actually match a bulk-exfiltration shape:")
print(f"Caught by the detector: {caught} ({100*caught/len(exfil_shaped):.1f}%)")
print(exfil_shaped[["Dst Port","orig_bytes","resp_bytes","byte_ratio","duration","if_anomaly"]].to_string(index=False))
