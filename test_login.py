import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import sqlite3
import json
from server.SocketServer import SocketServer
import threading
import time

def test_login():
    server = SocketServer(tcp_port=50015, udp_port=50016)
    server.start()
    
    time.sleep(1)
    
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 50015))
    
    print("Connected")
    packet = {
        "action": "LOGIN",
        "payload": {"username": "admin", "password_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
    }
    s.sendall(json.dumps(packet).encode('utf-8'))
    
    s.settimeout(2.0)
    try:
        resp = s.recv(4096)
        print("Response:", resp.decode())
    except Exception as e:
        print("Timeout or error:", e)
    finally:
        s.close()
        server.stop()

if __name__ == '__main__':
    test_login()
