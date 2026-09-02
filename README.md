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

Creates three network namespaces (attacker, victim, monitor) connected via a
bridge, with traffic mirroring so `monitor` passively sees all attacker↔victim
traffic without being a party to it (simulating a data diode).

```bash
bash setup_network.sh   # see script contents below, or in repo
```

## Generating traffic

```bash
./gen_benign.sh    # normal iperf3 / HTTP / one legit bulk upload
./gen_exfil.sh      # fast-burst + slow-trickle exfiltration
```

## Running the pipeline

```bash
cd analysis
python3 -m venv venv && source venv/bin/activate
pip install pandas numpy scikit-learn

python3 parse_zeek_v2.py          # combine all conn.log files into one CSV
python3 feature_engineering_v3.py # compute features
python3 combined_detector.py      # run detection, output alerts.csv
```

## Results (on this lab's dataset, 51 flows)

| Class      | Flows | Detected | Recall |
|------------|-------|----------|--------|
| exfil_fast | 3     | 3        | 100%   |
| exfil_slow | 35    | 35       | 100%   |
| benign     | 13    | 2 false positives | 85% specificity |

**Known limitation:** the detector cannot yet reliably distinguish a
legitimate one-off bulk transfer (e.g. a backup or cloud upload) from a
burst exfiltration event based on traffic shape alone — this is a real,
disclosed limitation, not a bug. Real systems typically resolve this with
additional context (destination reputation, user identity, DLP content
inspection) that a purely metadata-based passive monitor doesn't have
access to.

## Project structure
