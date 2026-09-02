#!/bin/bash
echo "--- Varied iperf3 runs ---"
for i in 1 2 3; do
  DURATION=$((RANDOM % 5 + 2))
  sudo ip netns exec victim iperf3 -s -D -p 520$i 2>/dev/null
  sleep 1
  sudo ip netns exec attacker iperf3 -c 10.10.10.3 -p 520$i -t $DURATION
  sleep 2
done

echo "--- Varied curl requests ---"
sudo ip netns exec victim bash -c "cd /tmp && mkdir -p www && echo 'page1' > www/page1.html && echo 'page2 with more content here' > www/page2.html && setsid nohup python3 -m http.server 8080 --directory www > /tmp/http.log 2>&1 < /dev/null &"
sleep 1
for path in page1.html page2.html page1.html; do
  sudo ip netns exec attacker curl -s http://10.10.10.3:8080/$path
  sleep 1
done

echo "--- Legitimate one-off bulk upload (false-positive stress test) ---"
sudo ip netns exec attacker dd if=/dev/urandom of=/tmp/legit_upload.bin bs=1M count=500 2>/dev/null
sudo ip netns exec victim bash -c "setsid nohup nc -l -p 7000 > /tmp/legit_received.bin 2>/tmp/nc7000.log < /dev/null &"
sleep 2
sudo ip netns exec attacker nc 10.10.10.3 7000 < /tmp/legit_upload.bin
echo "Benign traffic generation complete."
