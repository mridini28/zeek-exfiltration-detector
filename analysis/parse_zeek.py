import pandas as pd

def parse_conn_log(path, label):
    """Parse a Zeek conn.log file into a pandas DataFrame, tagging each row with a label."""
    with open(path) as f:
        lines = f.readlines()

    # Find the #fields line to get column names
    fields_line = [l for l in lines if l.startswith("#fields")][0]
    columns = fields_line.strip().split("\t")[1:]

    # Data rows are the ones that don't start with '#'
    data_rows = [l.strip().split("\t") for l in lines if not l.startswith("#")]

    df = pd.DataFrame(data_rows, columns=columns)
    df["label"] = label
    return df

if __name__ == "__main__":
    benign = parse_conn_log("../logs/benign/conn.log", "benign")
    exfil_fast = parse_conn_log("../logs/exfil_fast/conn.log", "exfil_fast")
    exfil_slow = parse_conn_log("../logs/exfil_slow/conn.log", "exfil_slow")

    all_data = pd.concat([benign, exfil_fast, exfil_slow], ignore_index=True)

    # Convert numeric columns
    numeric_cols = ["ts", "duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts", "orig_ip_bytes", "resp_ip_bytes"]
    for col in numeric_cols:
        all_data[col] = pd.to_numeric(all_data[col], errors="coerce")

    all_data.to_csv("combined_flows.csv", index=False)
    print(f"Total flows: {len(all_data)}")
    print(all_data["label"].value_counts())
    print("\nSaved to combined_flows.csv")
