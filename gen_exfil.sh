#!/bin/bash
echo "--- Fast burst exfil, varied sizes ---"
for i in 1 2 3; do
  SIZE_MB=$((50 * i))
  PORT=$((9990 + i))
  sudo ip netns exec attacker dd if=/dev/urandom of=/tmp/exfil_$i.bin bs=1M count=$SIZE_MB 2>/dev/null
  sudo ip netns exec victim bash -c "setsid nohup nc -l -p $PORT > /tmp/recv_$i.bin 2>/tmp/nc_$i.log < /dev/null &"
  sleep 1
  sudo ip netns exec attacker nc 10.10.10.3 $PORT < /tmp/exfil_$i.bin
  sleep 1
done

echo "--- Slow trickle, varied chunk size/interval ---"
sudo ip netns exec attacker dd if=/dev/urandom of=/tmp/chunk2.bin bs=1K count=20 2>/dev/null
for i in $(seq 1 15); do
  sudo ip netns exec victim bash -c "setsid nohup nc -l -p 9989 > /tmp/trickle2_$i.bin 2>/tmp/nc_t2.log < /dev/null &"
  sleep 0.3
  sudo ip netns exec attacker nc -q1 10.10.10.3 9989 < /tmp/chunk2.bin
  sleep 3
done

echo "Exfil traffic generation complete."
