import pandas as pd

usecols = ["Dst Port", "Flow Duration", "TotLen Fwd Pkts", "TotLen Bwd Pkts", "Label"]
df = pd.read_csv("../real_data/Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv", usecols=usecols, low_memory=False)
df = df[df["Label"].isin(["Benign", "Infilteration"])].copy()

df["Flow Duration"] = pd.to_numeric(df["Flow Duration"], errors="coerce").fillna(0) / 1_000_000
df["TotLen Fwd Pkts"] = pd.to_numeric(df["TotLen Fwd Pkts"], errors="coerce").fillna(0)
df["TotLen Bwd Pkts"] = pd.to_numeric(df["TotLen Bwd Pkts"], errors="coerce").fillna(0)
df["byte_ratio"] = df["TotLen Fwd Pkts"] / (df["TotLen Bwd Pkts"] + 1)

print("=== orig_bytes (fwd) ===")
print(df.groupby("Label")["TotLen Fwd Pkts"].describe())
print("\n=== resp_bytes (bwd) ===")
print(df.groupby("Label")["TotLen Bwd Pkts"].describe())
print("\n=== byte_ratio ===")
print(df.groupby("Label")["byte_ratio"].describe())
print("\n=== duration (sec) ===")
print(df.groupby("Label")["Flow Duration"].describe())
