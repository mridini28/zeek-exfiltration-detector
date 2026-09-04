import pandas as pd

usecols = ["Dst Port", "Flow Duration", "TotLen Fwd Pkts", "TotLen Bwd Pkts", "Label"]
df = pd.read_csv("../real_data/Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv", usecols=usecols, low_memory=False)
df = df[df["Label"] == "Infilteration"].copy()

df["TotLen Fwd Pkts"] = pd.to_numeric(df["TotLen Fwd Pkts"], errors="coerce").fillna(0)
df["TotLen Bwd Pkts"] = pd.to_numeric(df["TotLen Bwd Pkts"], errors="coerce").fillna(0)
df["byte_ratio"] = df["TotLen Fwd Pkts"] / (df["TotLen Bwd Pkts"] + 1)

exfil_shaped = df[(df["byte_ratio"] > 10) & (df["TotLen Fwd Pkts"] > 10000)]
print(f"Total Infiltration flows: {len(df)}")
print(f"Flows that actually LOOK like bulk exfiltration (byte_ratio>10, orig_bytes>10KB): {len(exfil_shaped)}")
print(f"That's {100*len(exfil_shaped)/len(df):.2f}% of the Infiltration label")
