import pandas as pd
import numpy as np

class HostBaseline:
    """
    Tracks per (source, destination, port) baseline behavior and
    flags flows/windows that deviate from that channel's own history.
    """
    def __init__(self, window_seconds=60, zscore_threshold=1.5):
        self.window_seconds = window_seconds
        self.zscore_threshold = zscore_threshold
        self.channel_history = {}  # (src,dst,port) -> list of (ts, orig_bytes)

    def update(self, src, dst, port, ts, orig_bytes):
        key = (src, dst, port)
        self.channel_history.setdefault(key, []).append((ts, orig_bytes))

    def score_channel(self, src, dst, port):
        """Returns dict with baseline stats + whether current volume is anomalous."""
        key = (src, dst, port)
        history = self.channel_history.get(key, [])
        if len(history) < 2:
            return {"channel": key, "status": "insufficient_history", "num_flows": len(history)}

        df = pd.DataFrame(history, columns=["ts", "orig_bytes"])
        t0 = df["ts"].min()
        df["window"] = ((df["ts"] - t0) // self.window_seconds).astype(int)
        windowed = df.groupby("window")["orig_bytes"].sum().reset_index()

        mean = windowed["orig_bytes"].mean()
        std = windowed["orig_bytes"].std(ddof=0)
        latest = windowed["orig_bytes"].iloc[-1]

        zscore = (latest - mean) / std if std > 0 else 0
        is_new_channel = len(history) <= 3  # arbitrary "still building history" cutoff

        return {
            "channel": key,
            "status": "new_channel" if is_new_channel else "established",
            "num_flows": len(history),
            "total_volume": df["orig_bytes"].sum(),
            "latest_window_volume": latest,
            "zscore": round(zscore, 2),
            "flagged": abs(zscore) > self.zscore_threshold and not is_new_channel
        }


if __name__ == "__main__":
    df = pd.read_csv("features_v2.csv").sort_values("ts")

    baseline = HostBaseline(window_seconds=60, zscore_threshold=1.5)
    for _, row in df.iterrows():
        baseline.update(row["id.orig_h"], row["id.resp_h"], row["id.resp_p"], row["ts"], row["orig_bytes"])

    print("=== Per-channel baseline scores ===\n")
    for key in baseline.channel_history:
        result = baseline.score_channel(*key)
        print(result)

    print("\n=== Special case: new channels with sustained regular volume ===")
    print("(This is the actual slow-trickle signature: new + high flow count + no burst)")
    for key, history in baseline.channel_history.items():
        num_flows = len(history)
        total = sum(b for _, b in history)
        if num_flows >= 5:  # repeated small transfers = suspicious regardless of z-score
            print(f"  {key}: {num_flows} flows, {total} total bytes -> SUSPICIOUS (repeated channel, new destination)")
