#!/usr/bin/env bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000
export MIMIAKA_MONGO_URL=mongodb://mimiaka:mimiaka1846@ds023668-a0.mlab.com:23668,ds023668-a1.mlab.com:23668/mimiaka?replicaSet=rs-ds023668
sudo apt install gnugo
cd ~/go-web-server
nohup python3 web.py &
