from PyQt5 import QtWidgets, QtGui, QtCore
import math

class GraphWidget(QtWidgets.QWidget):
    node_clicked = QtCore.pyqtSignal(int)
    edge_toggled = QtCore.pyqtSignal(int, int, bool)

    def __init__(self, n_nodes:int = 10, parent=None):
        super().__init__(parent)
        self.n = n_nodes
        self.radius = 220
        self.node_radius = 20
        self.center = None
        self.positions = {}
        self.edges = {}  # key (a,b) with a<b -> active bool
        self.init_positions()
        self.setMinimumSize(600, 600)
        
        # Animation state
        self.animation_active = False
        self.animation_progress = 0.0  # 0 to 1
        self.animation_from = None
        self.animation_to = None
        self.animation_timer = QtCore.QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_duration = 500  # ms
        self.animation_message = ""  # Message being sent
        self.animation_crc = ""  # CRC being sent
        
        # Error animation state
        self.error_animation_node = None
        self.error_animation_active = False
        self.error_animation_timer = QtCore.QTimer()
        self.error_animation_timer.timeout.connect(self.update_error_animation)
        self.error_animation_duration = 600  # ms
        self.error_animation_progress = 0.0
        
        # Node error state - dict with node_id -> True/False for having errors
        self.node_errors = {i: False for i in range(self.n)}

    def init_positions(self):
        self.positions = {}
        w = self.width() if self.width()>0 else 600
        h = self.height() if self.height()>0 else 600
        cx = w//2; cy = h//2
        self.center = (cx, cy)
        for i in range(self.n):
            ang = 2*math.pi*i/self.n - math.pi/2
            x = cx + int(self.radius*math.cos(ang))
            y = cy + int(self.radius*math.sin(ang))
            self.positions[i] = (x,y)
        # init fully connected edges
        self.edges = {}
        for i in range(self.n):
            for j in range(i+1, self.n):
                self.edges[(i,j)] = True

    def resizeEvent(self, event):
        self.init_positions()
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # background
        p.fillRect(self.rect(), QtGui.QColor(30,30,30))
        # draw edges
        pen = QtGui.QPen()
        pen.setWidth(2)
        for (a,b),active in self.edges.items():
            x1,y1 = self.positions[a]
            x2,y2 = self.positions[b]
            
            # Highlight the edge being used for transmission
            is_transmission_edge = (
                self.animation_active and 
                ((a == self.animation_from and b == self.animation_to) or 
                 (b == self.animation_from and a == self.animation_to))
            )
            
            if is_transmission_edge:
                # Animated edge highlighting
                pen.setStyle(QtCore.Qt.SolidLine)
                pen.setWidth(4)
                glow_intensity = int(255 * (0.5 + 0.5 * math.sin(self.animation_progress * math.pi * 4)))
                pen.setColor(QtGui.QColor(glow_intensity, 200, 50))
            elif active:
                pen.setStyle(QtCore.Qt.SolidLine)
                pen.setWidth(2)
                pen.setColor(QtGui.QColor(160,160,160))
            else:
                pen.setStyle(QtCore.Qt.DashLine)
                pen.setWidth(2)
                pen.setColor(QtGui.QColor(90,90,90))
            p.setPen(pen)
            p.drawLine(x1,y1,x2,y2)
        
        # Draw animation if active
        if self.animation_active and self.animation_from is not None and self.animation_to is not None:
            self.draw_animation(p)
        
        # draw nodes
        for i,(x,y) in self.positions.items():
            rect = QtCore.QRectF(x-self.node_radius, y-self.node_radius, self.node_radius*2, self.node_radius*2)
            
            # Determine node color based on state priority:
            # 1. Animation (highest priority)
            # 2. Node errors (red if has errors)
            # 3. Normal state (green)
            
            if self.animation_active:
                if i == self.animation_from:
                    # Sender node - red/orange with pulsing effect
                    pulse = 0.5 + 0.5 * math.sin(self.animation_progress * math.pi * 4)
                    node_color = QtGui.QColor(
                        int(220 * pulse),
                        int(100 * pulse),
                        int(50 * pulse)
                    )
                elif i == self.animation_to:
                    # Receiver node - blue/cyan
                    node_color = QtGui.QColor(50, 150, 220)
                else:
                    # Other nodes - check for errors
                    if self.node_errors.get(i, False):
                        node_color = QtGui.QColor(220, 80, 80)  # Red for error
                    else:
                        node_color = QtGui.QColor(120, 200, 140)
            elif self.error_animation_active and i == self.error_animation_node:
                # Error node - red with flash effect
                flash = 0.5 + 0.5 * math.cos(self.error_animation_progress * math.pi * 3)
                node_color = QtGui.QColor(
                    int(220 + 35 * flash),
                    int(100 - 100 * flash),
                    int(50 - 50 * flash)
                )
            elif self.node_errors.get(i, False):
                # Permanent red for nodes with errors
                node_color = QtGui.QColor(220, 80, 80)
            else:
                # Normal color when no animation or errors
                node_color = QtGui.QColor(120, 200, 140)
            
            p.setBrush(QtGui.QBrush(node_color))
            p.setPen(QtGui.QPen(QtGui.QColor(200,200,200)))
            p.drawEllipse(rect)
            
            # Draw aura around sender/receiver nodes during animation
            if self.animation_active:
                if i == self.animation_from:
                    # Pulsing aura for sender
                    aura_size = self.node_radius + 8 + int(5 * math.sin(self.animation_progress * math.pi * 4))
                    aura_rect = QtCore.QRectF(x - aura_size, y - aura_size, aura_size * 2, aura_size * 2)
                    aura_color = QtGui.QColor(220, 100, 50, 80)
                    p.setPen(QtGui.QPen(aura_color, 2))
                    p.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
                    p.drawEllipse(aura_rect)
                elif i == self.animation_to:
                    # Growing aura for receiver
                    aura_size = self.node_radius + 8 + int(5 * self.animation_progress)
                    aura_rect = QtCore.QRectF(x - aura_size, y - aura_size, aura_size * 2, aura_size * 2)
                    aura_color = QtGui.QColor(50, 150, 220, int(100 * (1 - self.animation_progress)))
                    p.setPen(QtGui.QPen(aura_color, 2))
                    p.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
                    p.drawEllipse(aura_rect)
            
            # Draw error indicator (X) if node has errors
            if self.node_errors.get(i, False):
                error_size = self.node_radius - 5
                p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2))
                p.drawLine(int(x - error_size), int(y - error_size), int(x + error_size), int(y + error_size))
                p.drawLine(int(x - error_size), int(y + error_size), int(x + error_size), int(y - error_size))
            
            # label
            p.setPen(QtGui.QPen(QtGui.QColor(20,20,20)))
            f = p.font(); f.setBold(True)
            p.setFont(f)
            p.drawText(rect, QtCore.Qt.AlignCenter, str(i))

    def mousePressEvent(self, event):
        pos = event.pos()
        # check nodes first
        for i,(x,y) in self.positions.items():
            dx = pos.x() - x; dy = pos.y() - y
            if dx*dx + dy*dy <= self.node_radius*self.node_radius:
                self.node_clicked.emit(i)
                return
        # otherwise check edges (nearest line)
        for (a,b),active in list(self.edges.items()):
            x1,y1 = self.positions[a]
            x2,y2 = self.positions[b]
            # distance from point to segment
            dist = self._point_line_distance(pos.x(), pos.y(), x1,y1,x2,y2)
            if dist < 6:
                # toggle
                new_state = not active
                self.edges[(a,b)] = new_state
                self.edge_toggled.emit(a,b,new_state)
                self.update()
                return

    def _point_line_distance(self, px,py, x1,y1,x2,y2):
        # distance from point p to segment (x1,y1)-(x2,y2)
        dx = x2-x1; dy = y2-y1
        if dx==0 and dy==0:
            return math.hypot(px-x1, py-y1)
        t = ((px-x1)*dx + (py-y1)*dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        projx = x1 + t*dx; projy = y1 + t*dy
        return math.hypot(px-projx, py-projy)

    def start_animation(self, from_node: int, to_node: int, message: str = "", crc: str = "", duration_ms: int = 500):
        """Start animation from one node to another"""
        self.animation_from = from_node
        self.animation_to = to_node
        self.animation_progress = 0.0
        self.animation_active = True
        self.animation_duration = duration_ms
        self.animation_message = message
        self.animation_crc = crc
        self.animation_timer.start(30)  # 30ms per frame (~33 FPS)
        self.update()

    def update_animation(self):
        """Update animation progress"""
        if not self.animation_active:
            return
        
        self.animation_progress += 30.0 / self.animation_duration
        
        if self.animation_progress >= 1.0:
            self.animation_progress = 1.0
            self.animation_active = False
            self.animation_timer.stop()
        
        self.update()

    def draw_animation(self, painter: QtGui.QPainter):
        """Draw the animated line showing data transmission"""
        if self.animation_from is None or self.animation_to is None:
            return
        
        x1, y1 = self.positions[self.animation_from]
        x2, y2 = self.positions[self.animation_to]
        
        # Current position along the line
        t = self.animation_progress
        current_x = x1 + t * (x2 - x1)
        current_y = y1 + t * (y2 - y1)
        
        # Draw animated packet
        packet_size = 15
        packet_color = QtGui.QColor(255, 200, 50)  # Orange color
        painter.setBrush(QtGui.QBrush(packet_color))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 100), 2))
        painter.drawEllipse(QtCore.QRectF(
            current_x - packet_size/2,
            current_y - packet_size/2,
            packet_size,
            packet_size
        ))
        
        # Draw trail effect (fading line behind the packet)
        trail_pen = QtGui.QPen()
        trail_pen.setWidth(3)
        trail_color = QtGui.QColor(255, 200, 50, int(255 * (1 - t)))
        trail_pen.setColor(trail_color)
        painter.setPen(trail_pen)
        painter.drawLine(int(x1), int(y1), int(current_x), int(current_y))
        
        # Draw info text along the path
        if self.animation_message or self.animation_crc:
            # Calculate text position slightly above the packet
            text_x = current_x
            text_y = current_y - 20
            
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 100)))
            painter.setFont(QtGui.QFont("Arial", 8, QtGui.QFont.Bold))
            
            info_text = f"{self.animation_from}→{self.animation_to}"
            if self.animation_message:
                info_text += f"\n'{self.animation_message}'"
            
            painter.drawText(int(text_x - 30), int(text_y - 15), 60, 30, 
                           QtCore.Qt.AlignCenter, info_text)

    def is_edge_active(self, a: int, b: int) -> bool:
        """Check if edge between two nodes is active"""
        if a == b:
            return False
        key = (min(a, b), max(a, b))
        return self.edges.get(key, False)

    def toggle_edge(self, a: int, b: int):
        """Toggle edge state and emit signal"""
        if a == b:
            return
        key = (min(a, b), max(a, b))
        new_state = not self.edges.get(key, False)
        self.edges[key] = new_state
        self.edge_toggled.emit(a, b, new_state)
        self.update()

    def start_error_animation(self, node_id: int, duration_ms: int = 600):
        """Start animation showing error on a node"""
        self.error_animation_node = node_id
        self.error_animation_progress = 0.0
        self.error_animation_active = True
        self.error_animation_duration = duration_ms
        self.error_animation_timer.start(30)
        self.update()

    def update_error_animation(self):
        """Update error animation progress"""
        if not self.error_animation_active:
            return
        
        self.error_animation_progress += 30.0 / self.error_animation_duration
        
        if self.error_animation_progress >= 1.0:
            self.error_animation_progress = 1.0
            self.error_animation_active = False
            self.error_animation_timer.stop()
        
        self.update()

    def set_node_errors(self, node_id: int, has_errors: bool):
        """Set whether a node has errors (shows red permanently)"""
        if 0 <= node_id < self.n:
            self.node_errors[node_id] = has_errors
            self.update()

    def get_node_errors(self, node_id: int) -> bool:
        """Check if a node has errors"""
        if 0 <= node_id < self.n:
            return self.node_errors[node_id]
        return False

