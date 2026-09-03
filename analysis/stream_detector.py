import time
import sys
from datetime import datetime
import pandas as pd
import joblib

MODEL_PATH = "trained_model.joblib"
CONN_LOG_PATH = sys.argv[1] if len(sys.argv) > 1 else "../logs/live/conn.log"

COMMON_PORTS = {
    80: "http", 443: "https", 22: "ssh", 21: "ftp",
    5201: "iperf3_test", 5202: "iperf3_test", 5203: "iperf3_test",
    8080: "http_alt", 53: "dns"
}

model = joblib.load(MODEL_PATH)
FEATURE_COLS = ["orig_bytes", "resp_bytes", "byte_ratio", "duration", "bytes_per_second", "hour_of_day"]

# In-memory channel history for the trickle/repetition rule (per source,dest,port)
channel_counts = {}

def parse_line(line, columns):
    fields = line.strip().split("\t")
    if len(fields) != len(columns):
        return None
    row = dict(zip(columns, fields))
    try:
        row["ts"] = float(row["ts"])
        row["duration"] = float(row["duration"]) if row["duration"] != "-" else 0.0
        row["orig_bytes"] = int(row["orig_bytes"]) if row["orig_bytes"] != "-" else 0
        row["resp_bytes"] = int(row["resp_bytes"]) if row["resp_bytes"] != "-" else 0
        row["id.resp_p"] = int(row["id.resp_p"])
    except (ValueError, KeyError):
        return None
    return row

def score_flow(row):
    byte_ratio = row["orig_bytes"] / (row["resp_bytes"] + 1)
    port_category = COMMON_PORTS.get(row["id.resp_p"], "unusual")
    is_unusual_port = port_category == "unusual"
    hour_of_day = datetime.fromtimestamp(row["ts"]).hour
    bytes_per_second = row["orig_bytes"] / max(row["duration"], 0.001)
    is_burst = row["duration"] < 2 and row["orig_bytes"] > 10000

    key = (row["id.orig_h"], row["id.resp_h"], row["id.resp_p"])
    channel_counts[key] = channel_counts.get(key, 0) + 1
    trickle_anomaly = channel_counts[key] >= 5
    new_channel = channel_counts[key] == 1

    X = pd.DataFrame([{
        "orig_bytes": row["orig_bytes"], "resp_bytes": row["resp_bytes"],
        "byte_ratio": byte_ratio, "duration": row["duration"],
        "bytes_per_second": bytes_per_second, "hour_of_day": hour_of_day,
        "is_burst": int(is_burst), "is_unusual_port": int(is_unusual_port),
        "new_channel": int(new_channel)
    }])[FEATURE_COLS + ["is_burst", "is_unusual_port", "new_channel"]]

    if_anomaly = model.predict(X)[0] == -1

    reasons = []
    confidence = 0.0
    if if_anomaly:
        reasons.append("per-flow statistical anomaly (Isolation Forest)")
        confidence += 0.5
    if trickle_anomaly:
        reasons.append("repeated low-volume channel to new destination (possible slow exfiltration)")
        confidence += 0.6
    if is_unusual_port and byte_ratio > 100:
        reasons.append("unusual port with high outbound/inbound byte ratio")
        confidence += 0.2
    confidence = min(confidence, 1.0)

    return confidence, reasons

def tail_f(path):
    """Generator that yields new lines as they're appended to the file, like tail -f."""
    with open(path, "r") as f:
        pass  # read from start to capture header
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            yield line

def main():
    print(f"Streaming detector watching: {CONN_LOG_PATH}")
    columns = None
    for line in tail_f(CONN_LOG_PATH):
        if line.startswith("#fields"):
            columns = line.strip().split("\t")[1:]
            continue
        if line.startswith("#") or not columns:
            continue

        row = parse_line(line, columns)
        if row is None:
            continue

        t0 = time.time()
        confidence, reasons = score_flow(row)
        latency_ms = (time.time() - t0) * 1000

        if confidence > 0:
            print(f"[ALERT] ts={row['ts']:.3f} flow={row['uid']} "
                  f"{row['id.orig_h']}->{row['id.resp_h']}:{row['id.resp_p']} "
                  f"threat=data_exfiltration confidence={confidence:.2f} "
                  f"evidence=[{'; '.join(reasons)}] latency={latency_ms:.2f}ms")
        else:
            print(f"[ok] {row['id.orig_h']}->{row['id.resp_h']}:{row['id.resp_p']} normal ({latency_ms:.2f}ms)")

if __name__ == "__main__":
    main()
