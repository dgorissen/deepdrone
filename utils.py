import socket

def istcp(s):
    return s[:3] == "tcp"

def get_ip():
    return socket.gethostbyname(socket.getfqdn())
