import pandas as pd
import glob

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

if __name__ == "__main__":
    sources = [
        ("../logs/benign/conn.log", "benign"),
        ("../logs/benign_scaled/conn.log", "benign"),
        ("../logs/exfil_fast/conn.log", "exfil_fast"),
        ("../logs/exfil_scaled/conn_burst.log", "exfil_fast"),
        ("../logs/exfil_slow/conn.log", "exfil_slow"),
        ("../logs/exfil_trickle_scaled/conn.log", "exfil_slow"),
    ]

    dfs = [parse_conn_log(path, label) for path, label in sources]
    all_data = pd.concat(dfs, ignore_index=True)

    numeric_cols = ["ts", "duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts", "orig_ip_bytes", "resp_ip_bytes"]
    for col in numeric_cols:
        all_data[col] = pd.to_numeric(all_data[col], errors="coerce")

    all_data.to_csv("combined_flows_v2.csv", index=False)
    print(f"Total flows: {len(all_data)}")
    print(all_data["label"].value_counts())
    print("\nSaved to combined_flows_v2.csv")
