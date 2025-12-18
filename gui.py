import sys
import json
import socket
from PyQt5 import QtWidgets, QtGui, QtCore
from graph_widget import GraphWidget
from crc import create_frame

BASE_PORT = 12000

def send_control_to_node(node_id:int, payload:dict, timeout=2.0):
    port = BASE_PORT + node_id
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout) as s:
            s.sendall((json.dumps({'type':'control', **payload}) + '\n').encode('utf-8'))
            # read response
            data = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break
            if not data:
                return None
            return json.loads(data.decode('utf-8').strip())
    except Exception as e:
        return {'status':'error','reason':str(e)}

def send_message_to_node(node_id:int, payload:dict, timeout=3.0):
    port = BASE_PORT + node_id
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout) as s:
            s.sendall((json.dumps({'type':'message', **payload}) + '\n').encode('utf-8'))
            data = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break
            if not data:
                return None
            return json.loads(data.decode('utf-8').strip())
    except Exception as e:
        return {'status':'error','reason':str(e)}

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRC - Symulacja sieci (10 węzłów)")
        self.resize(1100, 700)
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        # left info panel
        self.info_panel = QtWidgets.QTextEdit()
        self.info_panel.setReadOnly(True)
        self.info_panel.setFixedWidth(220)
        self.info_panel.setHtml("<b>Wybierz węzeł</b>")
        layout.addWidget(self.info_panel)

        # center graph
        self.graph = GraphWidget(10)
        self.graph.node_clicked.connect(self.on_node_selected)
        self.graph.edge_toggled.connect(self.on_edge_toggled)
        layout.addWidget(self.graph, 1)

        # right control panel
        ctrl = QtWidgets.QWidget()
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl)
        # send segment
        ctrl_layout.addWidget(QtWidgets.QLabel("<b>Wysyłanie</b>"))
        row = QtWidgets.QHBoxLayout()
        self.sender_spin = QtWidgets.QSpinBox(); self.sender_spin.setRange(0,9)
        self.receiver_spin = QtWidgets.QSpinBox(); self.receiver_spin.setRange(0,9)
        row.addWidget(QtWidgets.QLabel("Nadawca:")); row.addWidget(self.sender_spin)
        row.addWidget(QtWidgets.QLabel("Adresat:")); row.addWidget(self.receiver_spin)
        ctrl_layout.addLayout(row)
        self.msg_edit = QtWidgets.QLineEdit()
        self.msg_edit.setPlaceholderText("Wiadomość")
        ctrl_layout.addWidget(self.msg_edit)
        self.crc_poly_edit = QtWidgets.QLineEdit("1010")
        self.crc_poly_edit.setPlaceholderText("wielomian CRC, np. 1011")
        ctrl_layout.addWidget(QtWidgets.QLabel("Wielomian CRC:"))
        ctrl_layout.addWidget(self.crc_poly_edit)
        self.send_btn = QtWidgets.QPushButton("Wyślij")
        self.send_btn.clicked.connect(self.on_send)
        ctrl_layout.addWidget(self.send_btn)

        ctrl_layout.addSpacing(10)
        # errors panel
        ctrl_layout.addWidget(QtWidgets.QLabel("<b>Wstrzykiwanie błędów</b>"))
        self.error_node_spin = QtWidgets.QSpinBox(); self.error_node_spin.setRange(0,9)
        ctrl_layout.addWidget(QtWidgets.QLabel("Węzeł:"))
        ctrl_layout.addWidget(self.error_node_spin)
        self.chk_bitflip = QtWidgets.QCheckBox("BIT_FLIP")
        self.chk_droppkt = QtWidgets.QCheckBox("DROP_PACKET")
        self.chk_delay = QtWidgets.QCheckBox("DELAY_PACKET")
        ctrl_layout.addWidget(self.chk_bitflip)
        ctrl_layout.addWidget(self.chk_droppkt)
        ctrl_layout.addWidget(self.chk_delay)
        self.apply_errors_btn = QtWidgets.QPushButton("Zastosuj błędy")
        self.apply_errors_btn.clicked.connect(self.on_apply_errors)
        ctrl_layout.addWidget(self.apply_errors_btn)
        self.repair_btn = QtWidgets.QPushButton("Napraw węzeł (usuń błędy)")
        self.repair_btn.clicked.connect(self.on_repair)
        ctrl_layout.addWidget(self.repair_btn)

        ctrl_layout.addStretch(1)

        layout.addWidget(ctrl, 0)

        # bottom console
        self.console = QtWidgets.QTextEdit()
        self.console.setReadOnly(True)
        console_dock = QtWidgets.QDockWidget("Konsola systemowa", self)
        console_dock.setWidget(self.console)
        console_dock.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, console_dock)

        # selected node
        self.selected_node = None

    def log(self, text:str):
        self.console.append(text)

    def on_node_selected(self, node_id:int):
        self.selected_node = node_id
        status = send_control_to_node(node_id, {'cmd':'get_status'})
        if status and status.get('status')=='ok':
            info = f"<b>Węzeł {node_id}</b><br>"
            info += f"Port: {BASE_PORT + node_id}<br>"
            info += "Błędy:<br>"
            for k,v in status.get('errors', {}).items():
                info += f"- {k}: {'ON' if v else 'OFF'}<br>"
            lm = status.get('last_message')
            
            info += "<br>Ostatnia ramka CRC:<br>"
            if lm:
                info += (
                    f"od: {lm.get('from')}<br>"
                    f"CRC OK: {lm.get('crc_ok')}<br>"
                    f"Długość ramki (bity): {lm.get('frame_len')}"
                )
            else:
                info += "brak"

            self.info_panel.setHtml(info)
        else:
            self.info_panel.setHtml(f"<b>Węzeł {node_id}</b><br>Brak połączenia.")

    def on_edge_toggled(self, a:int, b:int, state:bool):
        self.log(f"Połączenie {a} <-> {b} ustawione na {'AKTYWNE' if state else 'NIEAKTYWNE'}")

    def on_send(self):
        sender = int(self.sender_spin.value())
        receiver = int(self.receiver_spin.value())

        if sender == receiver:
            self.log("Nie można wysłać do samego siebie.")
            return

        if not self.graph.is_edge_active(sender, receiver):
            self.log(f"Brak aktywnego połączenia {sender} ↔ {receiver}.")
            return

        message = self.msg_edit.text()
        poly = self.crc_poly_edit.text().strip()

        if not message or not poly:
            self.log("Brak wiadomości lub wielomianu CRC.")
            return

        try:
            frame_bits = create_frame(message, poly)
        except Exception as e:
            self.log(f"Błąd CRC: {e}")
            return

        self.log(
            f"Nadawca {sender} → {receiver} | "
            f"Dane: '{message}' | "
            f"CRC: {frame_bits[-(len(poly)-1):]}"
        )

        res = send_message_to_node(receiver, {
            'from': sender,
            'frame_bits': frame_bits,
            'crc_poly': poly
        })

        self.log(f"Odpowiedź węzła {receiver}: {res}")

    def on_apply_errors(self):
        node = int(self.error_node_spin.value())
        errors = []
        if self.chk_bitflip.isChecked(): errors.append('BIT_FLIP')
        if self.chk_droppkt.isChecked(): errors.append('DROP_PACKET')
        if self.chk_delay.isChecked(): errors.append('DELAY_PACKET')
        res = send_control_to_node(node, {'cmd':'set_errors','errors':errors})
        self.log(f"Ustawiono błędy na węźle {node}: {res}")
        if self.selected_node == node:
            self.on_node_selected(node)

    def on_repair(self):
        node = int(self.error_node_spin.value())
        res = send_control_to_node(node, {'cmd':'repair'})
        self.log(f"Naprawiono węzeł {node}: {res}")
        if self.selected_node == node:
            self.on_node_selected(node)

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec_()
