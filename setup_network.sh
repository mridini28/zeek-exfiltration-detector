#!/bin/bash
sudo ip netns add attacker
sudo ip netns add victim
sudo ip netns add monitor
sudo ip link add br0 type bridge
sudo ip link set br0 up
sudo ip link add veth-att type veth peer name veth-att-br
sudo ip link add veth-vic type veth peer name veth-vic-br
sudo ip link add veth-mon type veth peer name veth-mon-br
sudo ip link set veth-att netns attacker
sudo ip link set veth-vic netns victim
sudo ip link set veth-mon netns monitor
sudo ip link set veth-att-br master br0
sudo ip link set veth-vic-br master br0
sudo ip link set veth-mon-br master br0
sudo ip link set veth-att-br up
sudo ip link set veth-vic-br up
sudo ip link set veth-mon-br up
sudo ip netns exec attacker ip addr add 10.10.10.2/24 dev veth-att
sudo ip netns exec attacker ip link set veth-att up
sudo ip netns exec attacker ip link set lo up
sudo ip netns exec victim ip addr add 10.10.10.3/24 dev veth-vic
sudo ip netns exec victim ip link set veth-vic up
sudo ip netns exec victim ip link set lo up
sudo ip netns exec monitor ip addr add 10.10.10.4/24 dev veth-mon
sudo ip netns exec monitor ip link set veth-mon up
sudo ip netns exec monitor ip link set lo up
sudo ip netns exec monitor ip link set veth-mon promisc on
sudo tc qdisc add dev veth-att-br handle ffff: ingress
sudo tc filter add dev veth-att-br parent ffff: protocol all u32 match u32 0 0 action mirred egress mirror dev veth-mon-br
sudo tc qdisc add dev veth-vic-br handle ffff: ingress
sudo tc filter add dev veth-vic-br parent ffff: protocol all u32 match u32 0 0 action mirred egress mirror dev veth-mon-br
echo "Network topology ready."
