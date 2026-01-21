import sys
import json
import socket
import random
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

def get_node_status(node_id:int, timeout=2.0):
    """Get status of a node including its errors"""
    return send_control_to_node(node_id, {'cmd': 'get_status'}, timeout=timeout)

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

        ctrl_layout.addSpacing(10)
        # all nodes control
        ctrl_layout.addWidget(QtWidgets.QLabel("<b>Wszystkie węzły</b>"))
        row_all = QtWidgets.QHBoxLayout()
        self.enable_all_btn = QtWidgets.QPushButton("Włącz wszystkie")
        self.enable_all_btn.clicked.connect(self.on_enable_all)
        self.disable_all_btn = QtWidgets.QPushButton("Wyłącz wszystkie")
        self.disable_all_btn.clicked.connect(self.on_disable_all)
        row_all.addWidget(self.enable_all_btn)
        row_all.addWidget(self.disable_all_btn)
        ctrl_layout.addLayout(row_all)

        ctrl_layout.addSpacing(10)
        # repair all
        self.repair_all_btn = QtWidgets.QPushButton("Napraw wszystkie (usuń błędy)")
        self.repair_all_btn.clicked.connect(self.on_repair_all)
        ctrl_layout.addWidget(self.repair_all_btn)

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
        
        # Initialize node error states
        self.refresh_all_node_states()
        
        # Log startup message
        self.log("╔═══════════════════════════════════════════════════════════╗", "INFO")
        self.log("║ CRC - Symulacja sieci 10 komputerów                       ║", "INFO")
        self.log("║ Gotowe do wysyłania wiadomości                            ║", "INFO")
        self.log("╚═══════════════════════════════════════════════════════════╝", "INFO")

    def refresh_all_node_states(self):
        """Synchronize graph with current state of all nodes"""
        for node_id in range(10):
            status = send_control_to_node(node_id, {'cmd':'get_status'})
            if status and status.get('status') == 'ok':
                errors = status.get('errors', {})
                has_errors = any(errors.values())
                self.graph.set_node_errors(node_id, has_errors)
    def log(self, text:str, level:str="INFO"):
        """Log message with formatting
        
        Args:
            text: Message to log
            level: One of 'INFO', 'SUCCESS', 'ERROR', 'WARNING'
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color mapping for different log levels
        colors = {
            'INFO': '#87CEEB',      # Sky blue
            'SUCCESS': '#90EE90',   # Light green
            'ERROR': '#FF6B6B',     # Light red
            'WARNING': '#FFD700',   # Gold
            'DEBUG': '#D8BFD8'      # Thistle
        }
        
        color = colors.get(level, '#87CEEB')
        
        # Format message with timestamp and level
        html = f"""
        <div style="margin: 5px 0; padding: 5px; border-left: 3px solid {color}; background-color: #f8f8f8;">
            <span style="color: #888; font-size: 11px;">[{timestamp}]</span>
            <span style="color: {color}; font-weight: bold; margin-left: 8px;">[{level}]</span>
            <span style="color: #333; margin-left: 8px;">{text}</span>
        </div>
        """
        self.console.append(html)

    def on_node_selected(self, node_id:int):
        self.selected_node = node_id
        status = send_control_to_node(node_id, {'cmd':'get_status'})
        if status and status.get('status')=='ok':
            info = f"<b>Węzeł {node_id}</b><br>"
            info += f"Port: {BASE_PORT + node_id}<br>"
            info += "Błędy:<br>"
            
            # Get errors and update graph visualization
            errors = status.get('errors', {})
            has_errors = any(errors.values())
            self.graph.set_node_errors(node_id, has_errors)
            
            for k,v in errors.items():
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
        status = 'AKTYWNE ✓' if state else 'NIEAKTYWNE ✗'
        self.log(f"Połączenie {a} <→ {b} ustawione na {status}", 'SUCCESS')

    def on_send(self):
        sender = int(self.sender_spin.value())
        receiver = int(self.receiver_spin.value())

        if sender == receiver:
            self.log("Nie można wysłać do samego siebie.", 'ERROR')
            return

        if not self.graph.is_edge_active(sender, receiver):
            self.log(f"Brak aktywnego połączenia {sender} ↔ {receiver}.", 'WARNING')
            return

        message = self.msg_edit.text()
        poly = self.crc_poly_edit.text().strip()

        if not message or not poly:
            self.log("Brak wiadomości lub wielomianu CRC.", 'ERROR')
            return

        try:
            frame_bits = create_frame(message, poly)
        except Exception as e:
            self.log(f"Błąd CRC: {e}", 'ERROR')
            return

        crc_check = frame_bits[-(len(poly)-1):]
        self.log(
            f"📤 Nadawca {sender} → {receiver} | Dane: '{message}' | CRC: {crc_check}",
            'SUCCESS'
        )

        # Start animation with message info
        crc_bits = frame_bits[-(len(poly)-1):]
        self.graph.start_animation(sender, receiver, message=message, crc=crc_bits, duration_ms=800)

        # Send message after a short delay to allow animation to show
        QtCore.QTimer.singleShot(100, lambda: self.send_message_async(sender, receiver, message, poly, frame_bits))

    def send_message_async(self, sender: int, receiver: int, message: str, poly: str, frame_bits: str):
        """Send message to node (called during animation)"""
        
        # Check if sender has errors - apply them BEFORE sending
        sender_status = get_node_status(sender)
        print(f"[DEBUG] sender_status: {sender_status}")
        sender_errors = sender_status.get('errors', {}) if sender_status else {}
        print(f"[DEBUG] sender_errors: {sender_errors}")
        
        # Apply BIT_FLIP on sender side (before sending)
        if sender_errors.get('BIT_FLIP', False) and frame_bits:
            idx = random.randrange(len(frame_bits))
            original_bit = frame_bits[idx]
            flipped = '1' if frame_bits[idx] == '0' else '0'
            frame_bits = frame_bits[:idx] + flipped + frame_bits[idx+1:]
            print(f"[DEBUG] BIT_FLIP applied at index {idx}")
            self.log(f"   [SENDER {sender}] BIT_FLIP: zmieniono bit {idx}: '{original_bit}' -> '{flipped}'", 'WARNING')
        else:
            print(f"[DEBUG] No BIT_FLIP: BIT_FLIP={sender_errors.get('BIT_FLIP', False)}, frame_bits empty={not frame_bits}")
        
        res = send_message_to_node(receiver, {
            'from': sender,
            'frame_bits': frame_bits,
            'crc_poly': poly
        })

        if res and res.get('status') == 'received':
            crc_ok = res.get('crc_ok')
            frame_len = res.get('frame_len', 'N/A')
            delay = res.get('delay', None)
            
            delay_str = f" | ⏱️ Opóźnienie: {delay}s" if delay else ""
            
            if crc_ok:
                # CRC check passed
                self.log(f"📥 Węzeł {receiver} odebrał | ✓ CRC OK | Rozmiar: {frame_len} bit{delay_str}", 'SUCCESS')
            else:
                # CRC check FAILED - data corrupted!
                self.log(f"📥 Węzeł {receiver} odebrał ramkę | ❌ CRC BŁĄD! Dane uszkodzone | Rozmiar: {frame_len} bit{delay_str}", 'ERROR')
                self.log(f"   └─ Przyczyna: Błąd w transmisji (np. BIT_FLIP, szum sieciowy)", 'DEBUG')
        elif res and res.get('status') == 'dropped':
            self.log(f"⚠️ Węzeł {receiver} odrzucił pakiet (DROP_PACKET) - pakiet nigdy nie dotarł", 'WARNING')
        else:
            self.log(f"❌ Błąd komunikacji z węzłem {receiver}: {res}", 'ERROR')

    def on_apply_errors(self):
        node = int(self.error_node_spin.value())
        errors = []
        if self.chk_bitflip.isChecked(): errors.append('BIT_FLIP')
        if self.chk_droppkt.isChecked(): errors.append('DROP_PACKET')
        if self.chk_delay.isChecked(): errors.append('DELAY_PACKET')
        res = send_control_to_node(node, {'cmd':'set_errors','errors':errors})
        
        # Update graph to show node with errors
        has_errors = len(errors) > 0
        self.graph.set_node_errors(node, has_errors)
        
        if res and res.get('status') == 'ok':
            errors_str = ', '.join(errors) if errors else 'brak'
            self.log(f"⚡ Błędy ustawione na węźle {node}: {errors_str}", 'WARNING')
        else:
            self.log(f"❌ Błąd przy ustawianiu błędów na węźle {node}", 'ERROR')
        if self.selected_node == node:
            self.on_node_selected(node)

    def on_repair(self):
        node = int(self.error_node_spin.value())
        res = send_control_to_node(node, {'cmd':'repair'})
        
        # Update graph to remove error indicator
        self.graph.set_node_errors(node, False)
        
        if res and res.get('status') == 'ok':
            self.log(f"✅ Węzeł {node} naprawiony - wszystkie błędy usunięte", 'SUCCESS')
        else:
            self.log(f"❌ Błąd przy naprawie węzła {node}", 'ERROR')
        if self.selected_node == node:
            self.on_node_selected(node)

    def on_enable_all(self):
        """Włącz wszystkie węzły (aktywuj wszystkie krawędzie)"""
        self.log("🔌 Włączanie wszystkich węzłów...", 'INFO')
        for i in range(10):
            for j in range(i+1, 10):
                if not self.graph.is_edge_active(i, j):
                    self.graph.toggle_edge(i, j)
        self.log("✅ Wszystkie węzły włączone", 'SUCCESS')

    def on_disable_all(self):
        """Wyłącz wszystkie węzły (deaktywuj wszystkie krawędzie)"""
        self.log("🔌 Wyłączanie wszystkich węzłów...", 'INFO')
        for i in range(10):
            for j in range(i+1, 10):
                if self.graph.is_edge_active(i, j):
                    self.graph.toggle_edge(i, j)
        self.log("✅ Wszystkie węzły wyłączone", 'SUCCESS')

    def on_repair_all(self):
        """Napraw wszystkie węzły - usuń wszystkie błędy"""
        self.log("🔧 Naprawianie wszystkich węzłów...", 'INFO')
        for node in range(10):
            send_control_to_node(node, {'cmd':'repair'})
            self.graph.set_node_errors(node, False)
        self.log("✅ Wszystkie węzły naprawione - błędy usunięte", 'SUCCESS')
        if self.selected_node is not None:
            self.on_node_selected(self.selected_node)

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec_()
