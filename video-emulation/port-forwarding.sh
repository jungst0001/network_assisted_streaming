sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A PREROUTING -p tcp -d 192.168.0.104 --dport 8088 -j DNAT --to-destination 192.168.122.2:8088
sudo iptables -t nat -A PREROUTING -p tcp -d 192.168.0.104 --dport 8888 -j DNAT --to-destination 192.168.122.3:8888
# sudo iptables -t nat -A PREROUTING -p tcp -d 192.168.0.104 --dport 8889 -j DNAT --to-destination 192.168.122.3:8888
sudo iptables -I FORWARD -m state -d 192.168.122.0/24 --state NEW,RELATED,ESTABLISHED -j ACCEPT
