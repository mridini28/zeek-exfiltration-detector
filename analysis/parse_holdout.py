import pandas as pd

def parse_conn_log(path, label):
    with open(path) as f:
        lines = f.readlines()
    fields_line = [l for l in lines if l.startswith("#fields")][0]
    columns = fields_line.strip().split("\t")[1:]
    data_rows = [l.strip().split("\t") for l in lines if not l.startswith("#")]
    if not data_rows:
        return pd.DataFrame(columns=columns + ["label"])
    df = pd.DataFrame(data_rows, columns=columns)
    df["label"] = label
    return df

sources = [
    ("../logs/benign_holdout/conn.log", "benign"),
    ("../logs/exfil_fast_holdout/conn.log", "exfil_fast"),
    ("../logs/exfil_slow_holdout/conn.log", "exfil_slow"),
]

dfs = [parse_conn_log(path, label) for path, label in sources]
holdout = pd.concat(dfs, ignore_index=True)

numeric_cols = ["ts", "duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts", "orig_ip_bytes", "resp_ip_bytes"]
for col in numeric_cols:
    holdout[col] = pd.to_numeric(holdout[col], errors="coerce")

holdout.to_csv("holdout_flows.csv", index=False)
print(f"Total holdout flows: {len(holdout)}")
print(holdout["label"].value_counts())
