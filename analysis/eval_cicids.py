import pandas as pd
import joblib

print("Loading CIC-IDS2018 data (this may take a minute)...")
usecols = ["Dst Port", "Flow Duration", "TotLen Fwd Pkts", "TotLen Bwd Pkts", "Label"]
df = pd.read_csv("../real_data/Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv", usecols=usecols, low_memory=False)

# Drop the ~26 duplicated header rows that leaked into the data
df = df[df["Label"].isin(["Benign", "Infilteration"])].copy()

# Sample down for speed -- 20k benign + all infiltration is plenty to get a real recall/FP read
benign = df[df["Label"] == "Benign"].sample(n=20000, random_state=42)
infil = df[df["Label"] == "Infilteration"]
df = pd.concat([benign, infil], ignore_index=True)

df["Flow Duration"] = pd.to_numeric(df["Flow Duration"], errors="coerce").fillna(0) / 1_000_000  # microsec -> sec
df["TotLen Fwd Pkts"] = pd.to_numeric(df["TotLen Fwd Pkts"], errors="coerce").fillna(0)
df["TotLen Bwd Pkts"] = pd.to_numeric(df["TotLen Bwd Pkts"], errors="coerce").fillna(0)
df["Dst Port"] = pd.to_numeric(df["Dst Port"], errors="coerce").fillna(0).astype(int)

COMMON_PORTS = {80, 443, 22, 21, 53}

df["orig_bytes"] = df["TotLen Fwd Pkts"]
df["resp_bytes"] = df["TotLen Bwd Pkts"]
df["duration"] = df["Flow Duration"]
df["byte_ratio"] = df["orig_bytes"] / (df["resp_bytes"] + 1)
df["is_unusual_port"] = ~df["Dst Port"].isin(COMMON_PORTS)
df["bytes_per_second"] = df["orig_bytes"] / df["duration"].replace(0, 0.001)
df["is_burst"] = (df["duration"] < 2) & (df["orig_bytes"] > 10000)
df["hour_of_day"] = 12  # not reliably parseable from this file's timestamp format; neutral placeholder
df["new_channel"] = 0   # CANNOT be computed -- no IP addresses in this dataset (see note above)

model = joblib.load("trained_model.joblib")
FEATURE_COLS = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]
X = df[FEATURE_COLS].copy()
X["is_burst"] = df["is_burst"].astype(int)
X["is_unusual_port"] = df["is_unusual_port"].astype(int)
X["new_channel"] = df["new_channel"].astype(int)

df["if_anomaly"] = model.predict(X) == -1

print("\n=== Isolation Forest layer only, on REAL CIC-IDS2018 traffic ===")
print("(trickle/repetition rule NOT applicable -- this dataset has no IP addresses)")
print(df.groupby(["Label", "if_anomaly"]).size())

df.to_csv("cicids_eval_results.csv", index=False)
