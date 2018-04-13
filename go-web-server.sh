#!/usr/bin/env bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000
export MIMIAKA_MONGO_URL=mongodb+srv://mimiaka:mimiaka1846@mimiaka-family-uthsq.mongodb.net/mimiaka
sudo apt install gnugo
cd ~/go-web-server
nohup python3 web.py &
