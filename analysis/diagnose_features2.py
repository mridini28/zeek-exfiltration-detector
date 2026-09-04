import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 20)

usecols = ["Dst Port", "Flow Duration", "TotLen Fwd Pkts", "TotLen Bwd Pkts", "Label"]
df = pd.read_csv("../real_data/Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv", usecols=usecols, low_memory=False)
df = df[df["Label"].isin(["Benign", "Infilteration"])].copy()

df["Flow Duration"] = pd.to_numeric(df["Flow Duration"], errors="coerce").fillna(0) / 1_000_000
df["TotLen Fwd Pkts"] = pd.to_numeric(df["TotLen Fwd Pkts"], errors="coerce").fillna(0)
df["TotLen Bwd Pkts"] = pd.to_numeric(df["TotLen Bwd Pkts"], errors="coerce").fillna(0)
df["byte_ratio"] = df["TotLen Fwd Pkts"] / (df["TotLen Bwd Pkts"] + 1)

for col, name in [("TotLen Fwd Pkts", "orig_bytes"), ("TotLen Bwd Pkts", "resp_bytes"), ("byte_ratio", "byte_ratio"), ("Flow Duration", "duration_sec")]:
    print(f"\n=== {name}: median (50%) and mean by label ===")
    g = df.groupby("Label")[col]
    print("median:", g.median().to_dict())
    print("mean:  ", g.mean().to_dict())
