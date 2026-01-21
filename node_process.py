import socket
import threading
import json
import time
import random
from crc import check_frame


BASE_PORT = 12000
ERROR_TYPES = ('BIT_FLIP', 'DROP_PACKET', 'DELAY_PACKET')

class NodeServer:
    def __init__(self, node_id: int, base_port: int):
        self.node_id = node_id
        self.port = base_port + node_id
        self.errors = {e: False for e in ERROR_TYPES}
        self.last_message = None
        self.lock = threading.Lock()

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('127.0.0.1', self.port))
        srv.listen(5)
        print(f"[NODE {self.node_id}] Listening on {self.port}")

        while True:
            conn, _ = srv.accept()
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        with conn:
            data = conn.recv(8192).decode().strip()
            msg = json.loads(data)

            if msg['type'] == 'control':
                res = self.handle_control(msg)
            else:
                res = self.handle_message(msg)

            conn.sendall((json.dumps(res) + '\n').encode())

    def handle_control(self, msg):
        cmd = msg['cmd']

        if cmd == 'set_errors':
            with self.lock:
                for e in ERROR_TYPES:
                    self.errors[e] = e in msg['errors']
            return {'status': 'ok', 'errors': self.errors}

        if cmd == 'repair':
            with self.lock:
                for e in ERROR_TYPES:
                    self.errors[e] = False
            return {'status': 'ok', 'errors': self.errors}

        if cmd == 'get_status':
            return {
                'status': 'ok',
                'errors': self.errors,
                'last_message': self.last_message
            }

    def handle_message(self, msg):
        sender = msg.get('from')
        frame_bits = msg.get('frame_bits')
        poly = msg.get('crc_poly')

        delay_time = None

        # Check for DROP_PACKET error
        with self.lock:
            if self.errors.get('DROP_PACKET', False):
                return {'status': 'dropped', 'node': self.node_id}
            
            # Check for DELAY_PACKET error
            if self.errors.get('DELAY_PACKET', False):
                delay_time = random.uniform(0.5, 1.5)
                time.sleep(delay_time)

        try:
            crc_ok = check_frame(frame_bits, poly)
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}

        self.last_message = {
            'from': sender,
            'crc_ok': crc_ok,
            'frame_len': len(frame_bits)
        }

        response = {
            'status': 'received',
            'node': self.node_id,
            'from': sender,
            'crc_ok': crc_ok
        }
        
        if delay_time is not None:
            response['delay'] = round(delay_time, 2)

        return response


def run_node(node_id: int, base_port: int):
    server = NodeServer(node_id, base_port)
    server.start()

