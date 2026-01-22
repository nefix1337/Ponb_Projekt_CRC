import socket
import threading
import json
import time
import random
from crc import check_frame
from network_models import Node, Packet


BASE_PORT = 12000
ERROR_TYPES = ('BIT_FLIP', 'DROP_PACKET', 'DELAY_PACKET')

class NodeServer:
    def __init__(self, node_id: int, base_port: int):
        self.node = Node(
            node_id=node_id,
            port=base_port + node_id
        )
        self.lock = threading.Lock()

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('127.0.0.1', self.node.port))
        srv.listen(5)
        print(f"[NODE {self.node.node_id}] Listening on {self.node.port}")

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
                errors_to_enable = msg['errors']
                for e in ERROR_TYPES:
                    self.node.set_error(e, e in errors_to_enable)
            return {'status': 'ok', 'errors': self.node.errors}

        if cmd == 'repair':
            with self.lock:
                self.node.disable_all_errors()
            return {'status': 'ok', 'errors': self.node.errors}

        if cmd == 'get_status':
            return {
                'status': 'ok',
                'errors': self.node.errors,
                'last_message': self.node.last_message
            }

    def handle_message(self, msg):
        sender = msg.get('from')
        frame_bits = msg.get('frame_bits')
        poly = msg.get('crc_poly')
        message_text = msg.get('message', '')

        # Stwórz pakiet
        packet = Packet(sender, self.node.node_id, message_text, frame_bits, poly)

        delay_time = None
        with self.lock:
            # DROP_PACKET
            if self.node.errors['DROP_PACKET']:
                packet.status = 'dropped'
                self.node.add_packet(packet)
                return {'status': 'dropped', 'node': self.node.node_id}
            
            # DELAY_PACKET
            if self.node.errors['DELAY_PACKET']:
                delay_time = random.uniform(0.5, 1.5)
                packet.delay = delay_time
                time.sleep(delay_time)

        # Sprawdź CRC
        try:
            crc_ok = check_frame(frame_bits, poly)
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}

        packet.status = 'received'
        packet.crc_valid = crc_ok
        self.node.add_packet(packet)
        self.node.last_message = {'from': sender, 'crc_ok': crc_ok, 'message': message_text, 'frame_len': len(frame_bits), 'frame_bits': frame_bits}

        response = {'status': 'received', 'node': self.node.node_id, 'from': sender, 'crc_ok': crc_ok, 'frame_len': len(frame_bits)}
        if delay_time:
            response['delay'] = round(delay_time, 2)
        return response


def run_node(node_id: int, base_port: int):
    server = NodeServer(node_id, base_port)
    server.start()

