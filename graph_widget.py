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
            if active:
                pen.setStyle(QtCore.Qt.SolidLine)
                pen.setColor(QtGui.QColor(160,160,160))
            else:
                pen.setStyle(QtCore.Qt.DashLine)
                pen.setColor(QtGui.QColor(90,90,90))
            p.setPen(pen)
            p.drawLine(x1,y1,x2,y2)
        # draw nodes
        for i,(x,y) in self.positions.items():
            rect = QtCore.QRectF(x-self.node_radius, y-self.node_radius, self.node_radius*2, self.node_radius*2)
            p.setBrush(QtGui.QBrush(QtGui.QColor(120, 200, 140)))
            p.setPen(QtGui.QPen(QtGui.QColor(200,200,200)))
            p.drawEllipse(rect)
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

    def is_edge_active(self, a:int, b:int) -> bool:
        if a==b: return False
        key = (a,b) if a<b else (b,a)
        return self.edges.get(key, False)
