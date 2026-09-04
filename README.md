# Passive Data Exfiltration Detection — Prototype

Detects data exfiltration from passively-mirrored network traffic (data-diode
style, one-way monitoring), using a combination of per-flow anomaly detection
(Isolation Forest) and a channel-repetition rule to catch low-and-slow
exfiltration that per-flow analysis alone misses.

## What this does

- Simulates a small network (attacker / victim / monitor) using Linux network
  namespaces, with the monitor passively mirroring traffic — no return path,
  matching a real data-diode setup.
- Captures traffic with Zeek into flow-level logs (`conn.log`).
- Generates labeled benign and exfiltration traffic (fast burst + slow trickle).
- Extracts features (byte ratio, duration, port category, destination novelty,
  burst-vs-spread) from the flow logs.
- Trains an Isolation Forest on benign traffic only, to flag statistical
  anomalies.
- Layers a per-channel repetition rule (`HostBaseline` class) on top to catch
  slow/trickle exfiltration, which Isolation Forest alone cannot detect since
  it evaluates each flow independently.
- Combines both into a single alert score with supporting evidence.
- Runs as a live streaming detector (tails Zeek's log and scores flows within
  milliseconds), not just an end-of-run batch report.

## Requirements

- WSL2 (or native Linux) with Ubuntu 22.04
- Zeek (network security monitor) — https://zeek.org
- Python 3.10+, pip
- tcpdump, iperf3, netcat-openbsd

## Setup

```bash
sudo apt update
sudo apt install -y tcpdump iproute2 net-tools curl iperf3 netcat-openbsd \
  build-essential cmake make gcc g++ flex bison libpcap-dev libssl-dev \
  python3 python3-dev python3-pip zlib1g-dev

# Zeek (adjust xUbuntu_22.04 to your Ubuntu version if different)
echo 'deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_22.04/ /' | sudo tee /etc/apt/sources.list.d/security:zeek.list
curl -fsSL https://download.opensuse.org/repositories/security:zeek/xUbuntu_22.04/Release.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/security_zeek.gpg > /dev/null
sudo apt update
sudo apt install -y zeek
echo 'export PATH=/opt/zeek/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

## Building the lab network

```bash
bash setup_network.sh
```

Namespaces don't survive a WSL restart — if you get "Cannot open network
namespace" errors later, just rerun this script.

## Generating traffic and running the pipeline

```bash
cd analysis
python3 -m venv venv && source venv/bin/activate
pip install pandas numpy scikit-learn joblib

python3 parse_zeek_v2.py           # combine conn.log files into one CSV
python3 feature_engineering_v3.py  # compute features
python3 combined_detector.py       # run detection, output alerts.csv
python3 train_and_save_model.py    # train + save the Isolation Forest
python3 stream_detector.py ../logs/live/conn.log   # live/streaming mode
```

## Results

### On lab-generated (synthetic) traffic — 51 flows

| Class      | Flows | Detected | Recall |
|------------|-------|----------|--------|
| exfil_fast | 3     | 3        | 100%   |
| exfil_slow | 35    | 35       | 100%   |
| benign     | 13    | 2 false positives | 85% specificity |

Per-flow detection latency (streaming mode): ~5–14ms.

### Held-out generalization test

Re-ran the trained model and the unchanged ≥5-flow trickle threshold against
a second, independently generated batch of traffic using different chunk
sizes (35KB vs. 20KB) and timing intervals (~8.3s vs. ~4.3s) than the data
used for tuning.

**Result: 100% recall maintained (13/13 real attack flows caught)** — the
channel-repetition rule generalizes across timing/size variation rather than
memorizing the specific parameters it was tuned on. The same iperf3-style
false positive reproduced independently, confirming it's a genuine, stable
weakness rather than a one-off artifact.

### Validation against real-world attack traffic (CIC-IDS2018)

Ran the same trained model, unmodified, against the public CIC-IDS2018
dataset's "Infiltration" attack day — traffic neither generated nor shaped
by us.

- Naive evaluation against the full "Infiltration" label: **3.5% recall**
  (3,278 / 93,063). Investigation showed this label predominantly captures a
  different attack stage (small inbound payload delivery / initial
  compromise) with an inbound-heavy shape fundamentally different from bulk
  exfiltration — only 0.03% of the label (27/93,063 flows) actually matches
  an outbound-heavy exfiltration shape.
- **On that correctly-shaped subset: 92.6% recall (25/27)**, despite the
  model never having seen this data before. The 2 missed flows were both on
  port 443 (HTTPS) with moderate byte ratios — a genuinely ambiguous case
  that likely needs additional context (e.g. TLS metadata or destination
  reputation) beyond volume-based features alone.

Note: CIC-IDS2018's processed CSVs strip IP addresses, so only the
Isolation Forest layer could be tested against it — the channel-repetition
rule requires per-source tracking and could not be evaluated on this
dataset.

## Known limitations

- Cannot yet reliably distinguish a legitimate one-off bulk transfer (e.g. a
  backup or cloud upload) from a burst-exfiltration event by traffic shape
  alone — the same false positive reproduced on both synthetic and held-out
  lab data.
- Trained entirely on lab-generated synthetic traffic; real-world deployment
  would benefit from a more diverse training set, ideally including real
  attack traffic.
- Channel-repetition detection requires visibility into source/destination
  IPs — datasets or environments that anonymize IPs (like CIC-IDS2018's
  processed CSVs) limit evaluation to the per-flow anomaly layer only.
- Scope is limited to data exfiltration; the broader problem statement
  covers 5 additional threat categories (DDoS, botnet C2, DNS
  tunnelling/DGA, encrypted malware, port scanning) not implemented here.

## Project structure

```
exfil-lab/
|-- setup_network.sh              # namespace + bridge + mirroring setup
|-- ignore_checksums.zeek         # Zeek config fix for veth mirroring
|-- logs/                         # raw Zeek conn.log captures, per session
|-- real_data/                    # CIC-IDS2018 CSV (gitignored, download separately)
`-- analysis/
    |-- parse_zeek_v2.py          # combines conn.log files into one CSV
    |-- feature_engineering_v3.py
    |-- host_baseline.py          # per-channel baseline / trickle detection
    |-- combined_detector.py      # final combined scorer
    |-- train_and_save_model.py   # trains + saves the Isolation Forest
    |-- stream_detector.py        # live streaming detector
    |-- parse_holdout.py          # holdout generalization test
    |-- holdout_eval.py
    |-- eval_cicids.py            # real-world CIC-IDS2018 validation
    |-- diagnose_features.py      # root-cause analysis of CIC-IDS2018 result
    |-- diagnose_features2.py
    |-- diagnose_subset.py
    `-- diagnose_subset_recall.py
```
