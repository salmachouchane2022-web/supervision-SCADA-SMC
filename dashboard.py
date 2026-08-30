from __future__ import annotations
import math
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, QPointF, QRectF, QElapsedTimer
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QLinearGradient, QRadialGradient, QPolygonF, QPainterPath
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from mod_communication1 import PLCConnector

# ============================================================================
# CONFIGURATION
# ============================================================================
PLC_IP = os.getenv("SMC_PLC_IP", "172.21.1.10") 
PLC_RACK = int(os.getenv("SMC_PLC_RACK", "0"))
PLC_SLOT = int(os.getenv("SMC_PLC_SLOT", "1"))
DB_NUMBER = 620
PLC_POLL_MS = 150
RECONNECT_MS = 2000
PLC_TIMEOUT_MS = 1500
DB_PATH = "smc_scada.db"

# Couleurs
BG = "#F1F5F9"
SURFACE = "#FFFFFF"
SURFACE_2 = "#E2E8F0"
BORDER = "#94A3B8"
BORDER_SOFT = "#CBD5E1"
TEXT = "#0F172A"
TEXT_2 = "#334155"
TEXT_3 = "#64748B"
GREEN = "#059669"
NEON_GREEN = "#00FF66"
AMBER = "#D97706"
RED = "#DC2626"
BLUE = "#2563EB"
TEAL_MIX = "#0D9488"
FONT = "Segoe UI"

# ============================================================================
# UTILITAIRES & DESSIN 3D
# ============================================================================
def qcolor(value: str, alpha: int = 255) -> QColor:
    color = QColor(value)
    color.setAlpha(alpha)
    return color

def app_font(size: int = 11, weight: int = QFont.Normal) -> QFont:
    return QFont(FONT, size, weight)

def make_label(text: str = "", size: int = 11, color: str = TEXT, weight: int = QFont.Normal, alignment=Qt.AlignLeft | Qt.AlignVCenter) -> QLabel:
    label = QLabel(text)
    label.setFont(app_font(size, weight))
    label.setStyleSheet(f"color:{color}; background:transparent;")
    label.setAlignment(alignment)
    return label

def draw_3d_glowing_button(painter: QPainter, width: int, height: int, base_color_hex: str, text: str, font_size: int = 13, animated: bool = False, phase: float = 0.0):
    base_color = QColor(base_color_hex)
    margin = 8
    rect = QRectF(margin, margin, width - 2*margin, height - 2*margin)
    radius = 12

    is_done = "DONE" in text.strip().upper()

    if is_done:
        neon_color = QColor(NEON_GREEN)
        pulse = 0.35 + 0.65 * (math.sin(phase * 4.5) + 1.0) / 2.0
        
        for i in range(8, 0, -1):
            halo_color = QColor(neon_color)
            alpha = int((42 * pulse) * ((9 - i) / 8.0))
            halo_color.setAlpha(max(0, min(255, alpha)))
            painter.setPen(QPen(halo_color, i * 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, radius, radius)
    else:
        glow_color = QColor(base_color)
        glow_color.setAlpha(30 if not animated else int(50 + 30 * math.sin(phase)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow_color)
        painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), radius+4, radius+4)

    if animated and not is_done:
        body_grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
        offset = (math.sin(phase) + 1) / 2.0
        c_green = QColor("#059669")
        c_blue = QColor("#2563EB")
        c_teal = QColor("#0D9488")

        body_grad.setColorAt(0.0, c_green)
        body_grad.setColorAt(max(0.0, min(1.0, offset)), c_teal)
        body_grad.setColorAt(1.0, c_blue)
    else:
        body_grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        body_grad.setColorAt(0.0, base_color.lighter(120))
        body_grad.setColorAt(0.5, base_color)
        body_grad.setColorAt(1.0, base_color.darker(160))
    
    painter.setBrush(body_grad)

    if is_done:
        neon_stroke = QColor(NEON_GREEN)
        neon_stroke.setAlpha(int(180 + 75 * pulse))
        painter.setPen(QPen(neon_stroke, 2.2 + 0.6 * pulse, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    else:
        painter.setPen(QPen(base_color.darker(180), 2))
        
    painter.drawRoundedRect(rect, radius, radius)

    face_margin_x = 3
    face_margin_y = 3
    face_rect = rect.adjusted(face_margin_x, face_margin_y, -face_margin_x, -face_margin_y-4)
    
    face_grad = QLinearGradient(0, face_rect.top(), 0, face_rect.bottom())
    if animated and not is_done:
        face_grad.setColorAt(0.0, QColor(255, 255, 255, 100))
        face_grad.setColorAt(1.0, QColor(255, 255, 255, 10))
    else:
        face_grad.setColorAt(0.0, base_color.lighter(150))
        face_grad.setColorAt(1.0, base_color.lighter(110))
    
    painter.setBrush(face_grad)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(face_rect, radius-2, radius-2)

    font = app_font(font_size, QFont.ExtraBold)
    font.setLetterSpacing(QFont.PercentageSpacing, 105)
    painter.setFont(font)
    
    painter.setPen(QPen(QColor(0, 0, 0, 150)))
    painter.drawText(face_rect.translated(1, 2), Qt.AlignCenter, text)
    
    painter.setPen(QPen(QColor("#FFFFFF")))
    painter.drawText(face_rect, Qt.AlignCenter, text)

class SignatureWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 32)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(QBrush(QColor("#F1F5F9")))
        painter.drawRoundedRect(rect, 6, 6)

        path = QPainterPath()
        path.moveTo(8, 24)
        path.lineTo(14, 21)
        path.quadTo(18, 13, 26, 17)
        path.cubicTo(45, -2, 60, -2, 48, 18)
        path.quadTo(38, 33, 24, 28)
        path.quadTo(12, 21, 28, 15)
        path.lineTo(125, 8)

        path.moveTo(55, 19)
        path.quadTo(58, 14, 61, 19)
        path.quadTo(66, 14, 69, 19)
        path.quadTo(74, 14, 77, 19)
        path.quadTo(82, 14, 85, 19)

        pen = QPen(QColor("#0F172A"), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setBrush(QBrush(QColor("#0F172A")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(16, 18, 2, 2)

        painter.setPen(QPen(QColor("#0F172A")))
        font = QFont("Segoe UI", 6, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.drawText(65, 27, "SALMA")

# ============================================================================
# WIDGETS GRAPHIQUES
# ============================================================================
class WindowButton(QToolButton):
    def __init__(self, symbol: str, hover_color: str = "#CBD5E1", parent=None):
        super().__init__(parent)
        self.setText(symbol)
        self.setFixedSize(38, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QToolButton {{ color:{TEXT_2}; background:transparent; border:none; border-radius:7px; font-size:16px; font-weight:600; }}
            QToolButton:hover {{ background:{hover_color}; color:{TEXT}; }}
            """
        )

class CycleTimerWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._both_stations_done = False
        self._table_running = False
        self._e_stop = False

        self._accumulated_ms = 0
        self._running = False
        self._elapsed = QElapsedTimer()

        self.setObjectName("CycleTimer")
        self.setMinimumSize(250, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(10)

        title = make_label("CYCLE TIMER", 12, TEXT, QFont.Bold, Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = make_label("STATION 2 • STATION 3", 9, TEXT_3, QFont.Bold, Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addStretch(1)

        self.display = QLabel("00:00:00")
        self.display.setObjectName("CycleTimerDisplay")
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setMinimumHeight(65)
        self.display.setFont(QFont("Consolas", 27, QFont.Bold))
        layout.addWidget(self.display)

        layout.addStretch(1)

        self.reset_button = QPushButton("RESET")
        self.reset_button.setObjectName("CycleTimerReset")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.setMinimumHeight(42)
        self.reset_button.setFont(QFont(FONT, 11, QFont.Bold))
        self.reset_button.clicked.connect(self.reset_timer)
        layout.addWidget(self.reset_button)

        self._display_timer = QTimer(self)
        self._display_timer.setTimerType(Qt.PreciseTimer)
        self._display_timer.timeout.connect(self._refresh_display)
        self._display_timer.start(100)

        self._apply_style()
        self._refresh_display()

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QFrame#CycleTimer {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            QLabel#CycleTimerDisplay {{
                background: #0F172A;
                color: #39FF88;
                border: 3px solid #475569;
                border-radius: 12px;
                padding: 6px 12px;
                selection-background-color: transparent;
            }}
            QPushButton#CycleTimerReset {{
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF4444, stop:0.48 #DC2626, stop:1 #991B1B);
                border: 2px solid #7F1D1D;
                border-top-color: #FCA5A5;
                border-radius: 10px;
                padding: 7px 18px;
                font-family: "{FONT}";
                font-size: 11pt;
                font-weight: 800;
            }}
            QPushButton#CycleTimerReset:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF5B5B, stop:0.5 #EF4444, stop:1 #B91C1C);
                border-color: #DC2626;
            }}
            QPushButton#CycleTimerReset:pressed {{
                background: #991B1B;
                border-top-color: #7F1D1D;
                border-bottom-color: #FCA5A5;
                padding-top: 10px;
                padding-bottom: 4px;
            }}
            """
        )

    def update_timer_state(self, both_stations_done: bool, table_running: bool, e_stop: bool):
        self._both_stations_done = bool(both_stations_done)
        self._table_running = bool(table_running)
        self._e_stop = bool(e_stop)

        should_run = (self._both_stations_done and not self._table_running and not self._e_stop)

        if should_run and not self._running:
            self._running = True
            self._elapsed.start()
        elif not should_run and self._running:
            self._freeze_running_time()

        self._update_display_style()
        self._refresh_display()

    def _freeze_running_time(self):
        if self._running and self._elapsed.isValid():
            self._accumulated_ms += self._elapsed.elapsed()
        self._elapsed.invalidate()
        self._running = False

    def reset_timer(self):
        self._freeze_running_time()
        self._accumulated_ms = 0
        self._refresh_display()
        self._update_display_style()

    def _current_elapsed_ms(self) -> int:
        value = self._accumulated_ms
        if self._running and self._elapsed.isValid():
            value += self._elapsed.elapsed()
        return max(0, int(value))

    def _format_time(self, milliseconds: int) -> str:
        total_seconds = milliseconds // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _refresh_display(self):
        self.display.setText(self._format_time(self._current_elapsed_ms()))

    def _update_display_style(self):
        if self._running:
            self.display.setStyleSheet("QLabel#CycleTimerDisplay { background: #0F172A; color: #39FF88; border: 3px solid #059669; border-radius: 12px; padding: 6px 12px; }")
        elif self._both_stations_done and (self._table_running or self._e_stop):
            self.display.setStyleSheet("QLabel#CycleTimerDisplay { background: #1E293B; color: #FBBF24; border: 3px solid #D97706; border-radius: 12px; padding: 6px 12px; }")
        else:
            self.display.setStyleSheet("QLabel#CycleTimerDisplay { background: #0F172A; color: #94A3B8; border: 3px solid #475569; border-radius: 12px; padding: 6px 12px; }")

class EStopWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 210)
        self.is_alarm = False
        self.blink_phase = 0.0

    def set_state(self, is_alarm: bool):
        self.is_alarm = is_alarm
        self.update()

    def advance_animation(self, delta: float = 0.15):
        self.blink_phase += delta
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        
        r_outer = 88.0
        r_bevel = 80.0
        r_face = 72.0

        def get_oct_polygon(radius: float, center_x: float, center_y: float) -> QPolygonF:
            pts = []
            for i in range(8):
                angle = math.pi / 8.0 + i * math.pi / 4.0
                pts.append(QPointF(center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
            return QPolygonF(pts)

        poly_outer = get_oct_polygon(r_outer, cx, cy)
        poly_bevel = get_oct_polygon(r_bevel, cx, cy)
        poly_face = get_oct_polygon(r_face, cx, cy)

        if self.is_alarm:
            alpha = int(140 + 115 * math.sin(self.blink_phase * 2.5))
            glow_color = QColor(220, 38, 38, alpha)
            c_light = QColor("#EF4444")
            c_base = QColor("#DC2626")
            c_dark = QColor("#7F1D1D")
        else:
            glow_color = QColor(5, 150, 105, 70)
            c_light = QColor("#10B981")
            c_base = QColor("#059669")
            c_dark = QColor("#064E3B")

        glow_grad = QRadialGradient(cx, cy, r_outer + 12)
        glow_grad.setColorAt(0.0, glow_color)
        glow_grad.setColorAt(0.7, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 20))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r_outer + 12, r_outer + 12)

        metal_grad = QLinearGradient(0, cy - r_outer, 0, cy + r_outer)
        metal_grad.setColorAt(0.0, QColor("#FFFFFF"))
        metal_grad.setColorAt(0.3, QColor("#CBD5E1"))
        metal_grad.setColorAt(0.7, QColor("#64748B"))
        metal_grad.setColorAt(1.0, QColor("#1E293B"))
        painter.setBrush(QBrush(metal_grad))
        painter.setPen(QPen(QColor("#0F172A"), 2))
        painter.drawPolygon(poly_outer)

        bevel_grad = QLinearGradient(0, cy - r_bevel, 0, cy + r_bevel)
        bevel_grad.setColorAt(0.0, c_dark.darker(140))
        bevel_grad.setColorAt(1.0, c_light.lighter(130))
        painter.setBrush(QBrush(bevel_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly_bevel)

        face_grad = QLinearGradient(0, cy - r_face, 0, cy + r_face)
        face_grad.setColorAt(0.0, c_light)
        face_grad.setColorAt(0.45, c_base)
        face_grad.setColorAt(1.0, c_dark)
        painter.setBrush(QBrush(face_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
        painter.drawPolygon(poly_face)

        shine_path = QPainterPath()
        shine_path.addPolygon(poly_face)
        glass_grad = QLinearGradient(0, cy - r_face, 0, cy)
        glass_grad.setColorAt(0.0, QColor(255, 255, 255, 170))
        glass_grad.setColorAt(0.85, QColor(255, 255, 255, 30))
        glass_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

        painter.save()
        painter.setClipPath(shine_path)
        painter.setBrush(QBrush(glass_grad))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(cx - r_face, cy - r_face, r_face * 2, r_face))
        painter.restore()

        inner_border = get_oct_polygon(r_face - 6, cx, cy)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPolygon(inner_border)

        font = app_font(16, QFont.ExtraBold)
        font.setLetterSpacing(QFont.PercentageSpacing, 102)
        painter.setFont(font)

        painter.setPen(QPen(QColor(0, 0, 0, 160)))
        painter.drawText(self.rect().translated(1, 2), Qt.AlignCenter, "E-STOP")

        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.drawText(self.rect(), Qt.AlignCenter, "E-STOP")

class CameraSensorWidget(QWidget):
    def __init__(self, state_color: str = BLUE, parent=None):
        super().__init__(parent)
        self.state_color = QColor(state_color)
        self.setMinimumHeight(65)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_color(self, color_hex: str):
        self.state_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cam_w, cam_h = 44, 14
        cx, cy = w / 2, 10

        cam_rect = QRectF(cx - cam_w/2, cy, cam_w, cam_h)
        painter.setPen(QPen(QColor("#334155"), 1.5))
        painter.setBrush(QBrush(QColor("#1E293B")))
        painter.drawRoundedRect(cam_rect, 4, 4)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#64748B")))
        painter.drawEllipse(QPointF(cx, cy + cam_h/2), 3, 3)

        beam_top_y = cy + cam_h
        beam_bottom_y = h - 4
        top_half_w = 6
        bottom_half_w = int(w * 0.38)

        beam_poly = QPolygonF([
            QPointF(cx - top_half_w, beam_top_y),
            QPointF(cx + top_half_w, beam_top_y),
            QPointF(cx + bottom_half_w, beam_bottom_y),
            QPointF(cx - bottom_half_w, beam_bottom_y)
        ])

        beam_grad = QLinearGradient(cx, beam_top_y, cx, beam_bottom_y)
        c_top = QColor(self.state_color)
        c_top.setAlpha(190)
        c_bot = QColor(self.state_color)
        c_bot.setAlpha(25)
        beam_grad.setColorAt(0.0, c_top)
        beam_grad.setColorAt(1.0, c_bot)

        painter.setBrush(QBrush(beam_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(beam_poly)

class IOBox(QFrame):
    def __init__(self, title: str, sub_prefix: str, has_camera: bool = False):
        super().__init__()
        self.sub_prefix = sub_prefix
        self.has_camera = has_camera
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        self.title_lbl = make_label(title, 12, TEXT, QFont.Bold, Qt.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        if self.has_camera:
            self.camera_widget = CameraSensorWidget(BLUE)
            layout.addWidget(self.camera_widget)
            
        self.inner_frame = QFrame()
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(4, 4, 4, 4)
        
        self.state_lbl = make_label(f"{sub_prefix} : WAITING", 11, TEXT, QFont.Bold, Qt.AlignCenter)
        inner_layout.addWidget(self.state_lbl)
        layout.addWidget(self.inner_frame)
        self.set_state("WAITING")
        
    def set_state(self, state: str):
        state_map = {"passed": "PASSED", "failed": "FAILED", "working": "RUNNING", "waiting": "WAITING"}
        display_state = state_map.get(state.lower(), state.upper())
        color = GREEN if state.lower() == "passed" else (RED if state.lower() == "failed" else (BLUE if state.lower() == "working" else TEXT_3))
        
        if self.has_camera:
            self.camera_widget.set_color(color)
            
        self.state_lbl.setText(f"{self.sub_prefix} : {display_state}")
        self.state_lbl.setStyleSheet(f"color:{color}; background:transparent;")
        self.inner_frame.setStyleSheet(f"background:rgba(255,255,255,0.7); border: 2px solid {color}; border-radius: 6px;")
        self.setStyleSheet(f"background:rgba(226,232,240,0.5); border: 1px solid {BORDER_SOFT}; border-radius: 8px;")

class RobotWidget(QWidget):
    def __init__(self, name: str, scale_factor: float = 1.0, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.name = name
        self.mode = "AUTO"
        self.state = "REST"
        self.running = False
        self.scale_factor = scale_factor
        self.angle = 0.0
        self.setMinimumSize(180, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, running: bool, mode: str = "AUTO", alarm: bool = False):
        self.running = running
        self.mode = mode.upper()
        if alarm:
            self.state = "STOP"
            self.mode = "ALARM"
        elif mode.upper() == "SERVICE":
            self.state = "MAINTENANCE"
        elif running:
            self.state = "WORKING"
        else:
            self.state = "DONE"
            
        self.update()

    def set_angle(self, angle: float):
        if self.running and self.state == "WORKING":
            self.angle = angle
        else:
            self.angle = 0.0
        self.update()

    def _status_color(self):
        if self.state == "WORKING": return qcolor(GREEN)
        if self.state == "DONE": return qcolor(GREEN)
        if self.state == "MAINTENANCE": return qcolor(AMBER)
        if self.state == "STOPPED": return qcolor(BLUE)
        if self.state in ("STOP", "REST"): return qcolor(RED)
        return qcolor(GREEN)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = max(1, self.width()), max(1, self.height())
        status = self._status_color()
        cx, base_y = w * 0.50, h * 0.55 
        sc = min(w / 180.0, h / 250.0) * self.scale_factor
        base_w, base_h = 90 * sc, 20 * sc
        
        halo = QColor(status)
        halo.setAlpha(25)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(QPointF(cx, base_y), 35 * sc, 35 * sc)
        
        base_grad = QLinearGradient(cx - base_w/2, base_y, cx + base_w/2, base_y)
        base_grad.setColorAt(0.0, qcolor("#64748B"))
        base_grad.setColorAt(0.5, qcolor("#94A3B8"))
        base_grad.setColorAt(1.0, qcolor("#475569"))
        painter.setBrush(QBrush(base_grad))
        painter.setPen(QPen(qcolor("#334155"), 2 * sc))
        painter.drawRoundedRect(int(cx - base_w / 2), int(base_y - base_h / 2), int(base_w), int(base_h), int(6 * sc), int(6 * sc))
        
        # --- MODIFICATION POUR MOUVEMENT D'ESSUIE-GLACE ---
        # Au lieu de bloquer l'angle de base à +40 (vers la droite), 
        # on centre l'angle autour de 0 (axe vertical) avec une bonne amplitude.
        a1 = math.radians(self.angle * 1.2) 
        a2 = math.radians(self.angle * 0.4 + 15)
        # --------------------------------------------------
        
        L1, L2 = 50 * sc, 40 * sc
        j0 = QPointF(cx, base_y - 10 * sc)
        j1 = QPointF(j0.x() + L1 * math.sin(a1), j0.y() - L1 * math.cos(a1))
        j2 = QPointF(j1.x() + L2 * math.sin(a2), j1.y() - L2 * math.cos(a2))
        arm_w = max(6, int(12 * sc))

        def draw_segment(p1, p2, width):
            painter.setPen(QPen(qcolor("#334155"), width + 2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
            painter.setPen(QPen(status, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
            highlight = QColor(255, 255, 255, 60)
            painter.setPen(QPen(highlight, width * 0.3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)

        draw_segment(j0, j1, arm_w)
        draw_segment(j1, j2, arm_w * 0.85)
        tool_len, gripper_w = 16 * sc, 8 * sc
        hx = j2.x() + tool_len * math.sin(a2)
        hy = j2.y() - tool_len * math.cos(a2)
        h_end = QPointF(hx, hy)
        
        painter.setPen(QPen(qcolor(TEXT_2), max(3, int(4 * sc)), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(j2, h_end)
        p1 = QPointF(hx - gripper_w * math.cos(a2), hy - gripper_w * math.sin(a2))
        p2 = QPointF(hx + gripper_w * math.cos(a2), hy + gripper_w * math.sin(a2))
        painter.setPen(QPen(status, max(3, int(4 * sc)), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(p1, p2)
        
        joint_r = max(4, int(8 * sc))
        for pt in [j0, j1, j2]:
            j_grad = QLinearGradient(pt.x() - joint_r, pt.y() - joint_r, pt.x() + joint_r, pt.y() + joint_r)
            j_grad.setColorAt(0, qcolor("#F1F5F9"))
            j_grad.setColorAt(1, qcolor("#334155"))
            painter.setPen(QPen(qcolor(TEXT), 1.5))
            painter.setBrush(QBrush(j_grad))
            painter.drawEllipse(pt, joint_r, joint_r)
            painter.setBrush(QBrush(qcolor(TEXT)))
            painter.drawEllipse(pt, joint_r * 0.4, joint_r * 0.4)
            
        text_y = int(base_y + base_h / 2 + 10 * sc)
        painter.setPen(QPen(qcolor(TEXT)))
        painter.setFont(app_font(max(12, int(13 * sc)), QFont.Bold))
        painter.drawText(0, text_y, w, int(20 * sc), Qt.AlignCenter, f"{self.name.upper()}")
        text_y += int(20 * sc)
        
        action_text = ""
        if self.state == "DONE": action_text = "DONE"
        elif self.state == "STOP": action_text = "STOP"
        elif self.state == "STOPPED": action_text = "STOPPED"
        elif self.state == "REST": action_text = "REST"
        elif self.state == "WORKING": action_text = "RUNNING"
        if action_text:
            painter.setPen(QPen(status))
            painter.setFont(app_font(max(11, int(12 * sc)), QFont.Bold))
            painter.drawText(0, text_y, w, int(18 * sc), Qt.AlignCenter, action_text)
            
        pill_text = self.mode
        pill_w = min(80 * sc, w * 0.60)
        pill_h = max(22, int(24 * sc))
        px = cx - pill_w / 2
        py = text_y + int(20 * sc)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(status))
        painter.drawRoundedRect(int(px), int(py), int(pill_w), int(pill_h), int(pill_h / 2), int(pill_h / 2))
        painter.setPen(QPen(qcolor("#FFFFFF")))
        painter.setFont(app_font(max(10, int(11 * sc)), QFont.Bold))
        painter.drawText(int(px), int(py), int(pill_w), int(pill_h), Qt.AlignCenter, pill_text)

class TurningTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.is_running = False
        self.angle = 0.0
        self.e_stop = False
        self.mode = "AUTO"
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, running: bool, mode: str = "AUTO", e_stop: bool = False):
        self.is_running = bool(running)
        self.mode = mode.upper()
        self.e_stop = bool(e_stop)
        self.update()

    def set_angle(self, angle: float):
        self.angle = angle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h - 40) 
        cx, cy = w / 2, (h - 40) / 2
        r = (side / 2) - 15
        r = max(60, min(r, 160))
        
        if self.is_running:
            status = qcolor(GREEN)
            label = "TURNING TABLE WORKING"
        else:
            status = qcolor(BLUE)
            label = "TABLE NOT TURNING"
        
        halo = QColor(status)
        halo.setAlpha(20)
        painter.setPen(QPen(halo, 8))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - r - 2), int(cy - r - 2), int((r + 2) * 2), int((r + 2) * 2))
        painter.setPen(QPen(status, 2, Qt.DashLine))
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        
        painter.save()
        painter.translate(cx, cy)
        
        if self.is_running and not self.e_stop: 
            painter.rotate(self.angle)
            
        plate_r = r - 12
        painter.setPen(QPen(qcolor(BORDER), 3))
        painter.setBrush(QBrush(qcolor(SURFACE_2)))
        painter.drawRoundedRect(int(-plate_r), int(-plate_r), int(plate_r * 2), int(plate_r * 2), 15, 15)
            
        hub = max(24, int(r * 0.30))
        painter.setBrush(QBrush(qcolor(SURFACE)))
        painter.setPen(QPen(status, 3))
        painter.drawEllipse(QPointF(0, 0), hub, hub)
        painter.setPen(QPen(qcolor(TEXT)))
        painter.setFont(app_font(max(11, int(r * 0.15)), QFont.Bold))
        painter.drawText(int(-hub), int(-hub * 0.40), int(hub * 2), int(hub * 0.80), Qt.AlignCenter, "SMC")
        painter.restore()
        
        badge_w, badge_h = 210, 26
        badge_x, badge_y = int(cx - badge_w / 2), int(cy + r + 15)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(status))
        painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 13, 13)
        painter.setPen(QPen(qcolor("#FFFFFF")))
        painter.setFont(app_font(11, QFont.Bold))
        painter.drawText(badge_x, badge_y, badge_w, badge_h, Qt.AlignCenter, label)

class GlowingLabelWidget(QWidget):
    def __init__(self, text: str = "", color: str = BLUE, font_size: int = 14, parent=None):
        super().__init__(parent)
        self._text = text
        self._color = color
        self._font_size = font_size
        self._animated = False
        self._phase = 0.0
        self.setMinimumHeight(52) 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, text: str, color: str, animated: bool = False):
        self._text = text
        self._color = color
        self._animated = animated
        self.update()

    def advance_animation(self, delta: float = 0.1):
        if self._animated:
            self._phase += delta
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        draw_3d_glowing_button(
            painter, self.width(), self.height(), self._color, self._text, 
            font_size=self._font_size, animated=self._animated, phase=self._phase
        )

class StationStatusWidget(QWidget):
    def __init__(self, process_name: str, parent=None):
        super().__init__(parent)
        self.process_name = process_name.upper()
        self.setMinimumHeight(115)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.mode_widget = GlowingLabelWidget(f"{self.process_name} • AUTO MODE", GREEN, 14)
        self.status_widget = GlowingLabelWidget("DONE", GREEN, 14)

        layout.addWidget(self.mode_widget)
        layout.addWidget(self.status_widget)

    def set_status(self, running: bool, mode: str = "AUTO", alarm: bool = False):
        mode_str = mode.upper()
        if mode_str == "SERVICE":
            mode_text = f"{self.process_name} • SERVICE MODE"
            mode_color = AMBER
        else:
            mode_text = f"{self.process_name} • AUTO MODE"
            mode_color = GREEN

        self.mode_widget.set_data(mode_text, mode_color, animated=False)

        if alarm:
            status_text = "STOPPED"
            status_color = RED
            animated = True
        elif running:
            status_text = "WORKING "
            status_color = TEAL_MIX
            animated = True
        else:
            status_text = "DONE"
            status_color = GREEN
            animated = True

        self.status_widget.set_data(status_text, status_color, animated=animated)

    def advance_animation(self):
        self.status_widget.advance_animation()

class TapeCassetteWidget(QWidget):
    COLOR_MAP = {1: (GREEN, "AVAILABLE"), 2: (RED, "NOT IN USE"), 3: (AMBER, "EMPTY"), 7: (BLUE, "IN USE")}

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.state = 1
        self.setMinimumHeight(55)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, state: int):
        self.state = int(state)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color_hex, text = self.COLOR_MAP.get(self.state, (TEXT_3, "UNKNOWN"))
        full_text = f"{self.name}\n{text}"
        draw_3d_glowing_button(painter, self.width(), self.height(), color_hex, full_text, font_size=11)

class TapeWallWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TapeWall")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)
        
        top_row = QHBoxLayout()
        top_row.addWidget(make_label("TAPE WALL", 12, TEXT, QFont.Bold))
        top_row.addStretch()
        
        counters_frame = QFrame()
        counters_frame.setStyleSheet(f"background:{SURFACE_2}; border:1px solid {BORDER}; border-radius:8px;")
        cf_layout = QHBoxLayout(counters_frame)
        cf_layout.setContentsMargins(12, 4, 12, 4)
        cf_layout.setSpacing(12)
        
        self.lbl_avail = make_label("AVAILABLE : 0", 11, GREEN, QFont.Bold)
        self.lbl_empty_amber = make_label("EMPTY : 0", 11, AMBER, QFont.Bold)
        self.lbl_in_use = make_label("IN USE : 0", 11, BLUE, QFont.Bold)
        self.lbl_notinuse = make_label("NOT IN USE : 0", 11, RED, QFont.Bold)
        
        cf_layout.addWidget(self.lbl_avail)
        cf_layout.addWidget(self.lbl_empty_amber)
        cf_layout.addWidget(self.lbl_in_use)
        cf_layout.addWidget(self.lbl_notinuse)
        
        top_row.addWidget(counters_frame)
        layout.addLayout(top_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.cassettes = []
        for idx in range(10):
            cassette = TapeCassetteWidget(f"T{idx+1}")
            self.cassettes.append(cassette)
            grid.addWidget(cassette, idx // 5, idx % 5)

        layout.addLayout(grid)
        self.setStyleSheet(f"QFrame#TapeWall {{ background:{SURFACE}; border:1px solid {BORDER_SOFT}; border-radius:12px; }}")

    def set_tape_states(self, states):
        states = list(states or [])[:10]
        while len(states) < 10:
            states.append(1)
        counts = {1: 0, 2: 0, 3: 0, 7: 0}
        for index, state in enumerate(states):
            self.cassettes[index].set_state(state)
            if state in counts:
                counts[state] += 1
                
        self.lbl_avail.setText(f"AVAILABLE : {counts[1]}")
        self.lbl_empty_amber.setText(f"EMPTY : {counts[3]}")
        self.lbl_in_use.setText(f"IN USE : {counts[7]}")
        self.lbl_notinuse.setText(f"NOT IN USE : {counts[2]}")

class EventLogWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EventLog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        
        title_lbl = make_label("SYSTEM EVENT LOG & ALARMS", 12, TEXT, QFont.ExtraBold)
        layout.addWidget(title_lbl)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["TIMESTAMP", "SOURCE", "EVENT DESCRIPTION"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setMaximumHeight(160)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        
        self.table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {SURFACE}; 
                alternate-background-color: #F8FAFC; 
                border: none;
                border-radius: 6px; 
                font-family: "{FONT}"; 
                font-size: 11pt; 
                color: {TEXT_2};
            }}
            QHeaderView::section {{
                background-color: {SURFACE_2}; 
                color: {TEXT}; 
                padding: 8px 12px; 
                border: none; 
                border-bottom: 2px solid {BORDER_SOFT}; 
                font-weight: 800; 
                font-size: 10pt;
                text-align: left;
            }}
            QTableWidget::item {{ 
                padding: 4px 12px; 
                border-bottom: 1px solid #E2E8F0; 
            }}
            """
        )
        
        table_container = QFrame()
        table_container.setStyleSheet(f"background:{SURFACE}; border:1px solid {BORDER_SOFT}; border-radius:8px;")
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(1, 1, 1, 1)
        tc_layout.addWidget(self.table)
        
        layout.addWidget(table_container)
        self.setStyleSheet(f"QFrame#EventLog {{ background:{SURFACE}; border:1px solid {BORDER_SOFT}; border-radius:12px; }}")

    def add_log(self, timestamp: str, source: str, message: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(timestamp))
        source_item = QTableWidgetItem(source)
        message_item = QTableWidgetItem(message)

        upper = f"{source} {message}".upper()
        if any(term in upper for term in ("ALARM", "ERROR", "FAILED", "E-STOP")):
            source_item.setForeground(QColor(RED))
            message_item.setForeground(QColor(RED))
            source_item.setFont(app_font(11, QFont.Bold))
            message_item.setFont(app_font(11, QFont.Bold))
        elif "PLC" in source.upper():
            source_item.setForeground(QColor(GREEN))
        elif "CYCLE" in source.upper():
            source_item.setForeground(QColor(BLUE))

        self.table.setItem(row, 1, source_item)
        self.table.setItem(row, 2, message_item)
        while self.table.rowCount() > 100:
            self.table.removeRow(0)
        self.table.scrollToBottom()

# ============================================================================
# THREAD DE COMMUNICATION PLC
# ============================================================================
class PLCWorker(QObject):
    dataReady = pyqtSignal(dict)
    connectionChanged = pyqtSignal(bool, str)
    stopRequested = pyqtSignal()

    def __init__(self, plc: PLCConnector, poll_ms: int, reconnect_ms: int):
        super().__init__()
        self.plc = plc
        self.poll_ms = poll_ms
        self.reconnect_ms = reconnect_ms
        self._connected = False
        self._poll_timer: Optional[QTimer] = None
        self._reconnect_timer: Optional[QTimer] = None
        self.stopRequested.connect(self.stop)

    def start(self):
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self.poll)
        self._poll_timer.start(self.poll_ms)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self.try_reconnect)
        self._reconnect_timer.start(self.reconnect_ms)

        if self.plc.connect():
            self._connected = True
            self.connectionChanged.emit(True, "")
        else:
            self._connected = False
            self.connectionChanged.emit(False, self.plc.last_error)

    def poll(self):
        values = self.plc.read_variables()
        if values is None:
            if self._connected:
                self._connected = False
                self.connectionChanged.emit(False, self.plc.last_error)
            return
        if not self._connected:
            self._connected = True
            self.connectionChanged.emit(True, "")
        self.dataReady.emit(values)

    def try_reconnect(self):
        if self._connected:
            return
        if self.plc.connect():
            self._connected = True
            self.connectionChanged.emit(True, "")

    def stop(self):
        if self._poll_timer: self._poll_timer.stop()
        if self._reconnect_timer: self._reconnect_timer.stop()
        try:
            self.plc.disconnect()
        except Exception:
            pass

# ============================================================================
# DASHBOARD PRINCIPAL SCADA
# ============================================================================
class SMCSupervisionDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMC — PLC SCADA | LEONI")
        self.setMinimumSize(1700, 950) 
        self.resize(1850, 1000)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        self._drag_pos = None
        self._last_values: Optional[Dict[str, Any]] = None
        self.last_plc_ok = False
        self.connected_to_plc = False
        self.rotation_angle = 0.0
        self.system_alarm = False

        self.init_db()

        self.setStyleSheet(
            f"""
            QMainWindow, QWidget#CentralWidget {{ background:{BG}; color:{TEXT}; font-family:"{FONT}"; }}
            QGroupBox {{ 
                background:{SURFACE}; border:1px solid {BORDER_SOFT}; border-radius:12px; 
                margin-top:28px; padding:25px 12px 16px 12px; color:{TEXT}; font-size:12pt; font-weight:800; 
            }}
            QGroupBox::title {{ 
                subcontrol-origin:margin; subcontrol-position: top left; left:12px; top:0px; 
                padding:4px 10px; color:{TEXT}; background:{SURFACE}; border:1px solid {BORDER_SOFT}; 
                border-radius:6px; font-size:11pt; font-weight:800; 
            }}
            QFrame#Header, QFrame#Chrome {{ background:{SURFACE}; border-radius:12px; border:1px solid {BORDER_SOFT}; }}
            QFrame#Chrome {{ border-bottom-left-radius:0; border-bottom-right-radius:0; border-bottom: none; }}
            QFrame#InfoTile {{ background:{SURFACE_2}; border:1px solid {BORDER_SOFT}; border-radius:8px; }}
            QLabel {{ background:transparent; }}
            """
        )

        self.init_ui()
        self.apply_connection_state(False)

        self.plc = PLCConnector(PLC_IP, PLC_RACK, PLC_SLOT, timeout_ms=PLC_TIMEOUT_MS)
        self.plc_thread = QThread(self)
        self.plc_worker = PLCWorker(self.plc, PLC_POLL_MS, RECONNECT_MS)
        self.plc_worker.moveToThread(self.plc_thread)

        self.plc_thread.started.connect(self.plc_worker.start)
        self.plc_worker.dataReady.connect(self.apply_variables)
        self.plc_worker.connectionChanged.connect(self.apply_connection_state)
        self.plc_thread.start()

        self.animation_timer = QTimer(self)
        self.animation_timer.setTimerType(Qt.PreciseTimer)
        self.animation_timer.timeout.connect(self.animate_graphics)
        self.animation_timer.start(33)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

    def init_db(self):
        self.db_conn = None
        self.db_cursor = None
        try:
            self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL
                )
            """)
            self.db_conn.commit()
        except Exception as exc:
            print(f"[DB ERROR] {exc}")

    def log_event(self, source: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            if self.db_cursor is not None:
                self.db_cursor.execute("INSERT INTO system_logs(timestamp, source, message) VALUES (?, ?, ?)", (timestamp, source, message))
                self.db_conn.commit()
        except Exception:
            pass
        if hasattr(self, "event_log_widget"):
            self.event_log_widget.add_log(timestamp, source, message)

    def _chrome_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _chrome_mouse_move(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _build_chrome(self, parent_layout):
        chrome = QFrame()
        chrome.setObjectName("Chrome")
        chrome.setFixedHeight(38)
        layout = QHBoxLayout(chrome)
        layout.setContentsMargins(12, 0, 4, 0)

        self.connection_led = QLabel("●")
        self.connection_led.setFont(app_font(10, QFont.Bold))
        layout.addWidget(self.connection_led)
        self.connection_text = make_label("PLC DISCONNECTED", 11, TEXT, QFont.Bold)
        layout.addWidget(self.connection_text)
        layout.addStretch()

        self.signature_widget = SignatureWidget()
        layout.addWidget(self.signature_widget)

        btn_min = WindowButton("—")
        btn_min.clicked.connect(self.showMinimized)
        self.btn_max = WindowButton("□")
        self.btn_max.clicked.connect(self._toggle_maximize)
        btn_close = WindowButton("×", hover_color="#FEE2E2")
        btn_close.clicked.connect(self.close)

        layout.addSpacing(10)
        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)

        parent_layout.addWidget(chrome)
        chrome.mousePressEvent = self._chrome_mouse_press
        chrome.mouseMoveEvent = self._chrome_mouse_move

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")

    def init_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._build_chrome(root)

        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 6, 14, 6)

        brand = QVBoxLayout()
        brand.addWidget(make_label("SMC", 20, BLUE, QFont.Bold))
        hl.addLayout(brand, 1)

        self.connection_tile = QFrame()
        self.connection_tile.setObjectName("InfoTile")
        ctl = QVBoxLayout(self.connection_tile)
        ctl.setContentsMargins(14, 6, 14, 6)
        self.plc_status_lbl = make_label("PLC : DISCONNECTED", 11, RED, QFont.Bold, Qt.AlignCenter)
        self.plc_info_lbl = make_label(f"S7 / DB{DB_NUMBER} / {PLC_IP}", 9, TEXT_3, QFont.Bold, Qt.AlignCenter)
        ctl.addWidget(self.plc_status_lbl)
        ctl.addWidget(self.plc_info_lbl)
        hl.addWidget(self.connection_tile)

        clock = QFrame()
        clock.setObjectName("InfoTile")
        cl = QVBoxLayout(clock)
        cl.setContentsMargins(14, 4, 14, 4)
        self.clock = make_label("00:00:00", 15, TEXT, QFont.Bold, Qt.AlignCenter)
        self.date_label = make_label("00/00/0000", 10, TEXT_3, QFont.Bold, Qt.AlignCenter)
        cl.addWidget(self.clock)
        cl.addWidget(self.date_label)
        hl.addWidget(clock)
        root.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        # STATION 1
        st1 = QGroupBox("STATION 1  •  LOADING / UNLOADING / TURNING TABLE")
        st1_layout = QVBoxLayout(st1)
        st1_layout.setSpacing(10)

        io_layout = QHBoxLayout()
        self.load_box = IOBox("LOADING", "AI INIT", True)
        self.unload_box = IOBox("UNLOADING", "AI END", True)
        io_layout.addWidget(self.load_box)
        io_layout.addWidget(self.unload_box)
        st1_layout.addLayout(io_layout)

        self.turning_table = TurningTableWidget()
        st1_layout.addWidget(self.turning_table, 1)
        grid.addWidget(st1, 0, 0)

        # STATION 2 - TAPING
        st2 = QGroupBox("STATION 2  •  TAPE STATION")
        st2_layout = QVBoxLayout(st2)
        st2_layout.setSpacing(10)
        self.status_st2 = StationStatusWidget("TAPING")
        st2_layout.addWidget(self.status_st2)
        self.robot1 = RobotWidget("ROBOT 1", scale_factor=1.1)
        st2_layout.addWidget(self.robot1, 1)
        grid.addWidget(st2, 0, 1)

        # STATION 3 - CLIPPING
        st3 = QGroupBox("STATION 3  •  CLIP STATION")
        st3.setStyleSheet(
            f"""
            QGroupBox {{ background: rgba(217, 119, 6, 0.04); border: 1px solid {AMBER}; border-radius: 12px; margin-top: 28px; padding: 25px 12px 16px 12px; color: {AMBER}; font-size: 12pt; font-weight: 800; }}
            QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position: top left; left:12px; top:0px; padding:4px 10px; color: {AMBER}; background: {SURFACE}; border: 1px solid {AMBER}; border-radius: 6px; }}
            """
        )
        st3_layout = QVBoxLayout(st3)
        st3_layout.setSpacing(10)
        self.status_st3 = StationStatusWidget("CLIPPING")
        st3_layout.addWidget(self.status_st3)

        robots = QHBoxLayout()
        self.robot2 = RobotWidget("ROBOT 2", scale_factor=1.1)
        self.robot3 = RobotWidget("ROBOT 3", scale_factor=1.1)
        robots.addWidget(self.robot2)
        robots.addWidget(self.robot3)
        st3_layout.addLayout(robots, 1)
        grid.addWidget(st3, 0, 2)

        # COLONNE DE DROITE : E-STOP & CYCLE TIMER
        right_col = QVBoxLayout()
        right_col.setSpacing(15)

        status_box = QGroupBox("EMERGENCY STOP")
        status_layout = QVBoxLayout(status_box)
        status_layout.setSpacing(10)
        status_layout.setContentsMargins(10, 15, 10, 10)
        
        self.e_stop = EStopWidget()
        status_layout.addWidget(self.e_stop, 0, Qt.AlignHCenter | Qt.AlignCenter)
        
        right_col.addWidget(status_box, 0)
        
        self.cycle_timer = CycleTimerWidget()
        right_col.addWidget(self.cycle_timer, 1)

        grid.addLayout(right_col, 0, 3)

        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 4)
        grid.setColumnStretch(3, 2)

        root.addLayout(grid, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self.tape_wall = TapeWallWidget()
        bottom.addWidget(self.tape_wall, 3)

        self.event_log_widget = EventLogWidget()
        bottom.addWidget(self.event_log_widget, 4)

        root.addLayout(bottom)

        self.log_event("SYSTEM", "SCADA interface initialized.")

    def apply_connection_state(self, connected: bool, error: str = ""):
        self.connected_to_plc = bool(connected)
        if self.connected_to_plc:
            self.connection_led.setStyleSheet(f"color:{GREEN}; background:transparent;")
            self.connection_text.setText("PLC CONNECTED")
            self.plc_status_lbl.setText("PLC : CONNECTED")
            self.plc_status_lbl.setStyleSheet(f"color:{GREEN}; background:transparent; font-weight:700;")
            if not self.last_plc_ok:
                self.log_event("PLC", f"Connected via Snap7 - {PLC_IP}")
        else:
            self.connection_led.setStyleSheet(f"color:{RED}; background:transparent;")
            self.connection_text.setText("PLC DISCONNECTED")
            self.plc_status_lbl.setText("PLC : DISCONNECTED")
            self.plc_status_lbl.setStyleSheet(f"color:{RED}; background:transparent; font-weight:700;")
            if self.last_plc_ok:
                message = "Communication lost. Reconnection in progress."
                if error: message += f" ({error})"
                self.log_event("PLC", message)

        self.last_plc_ok = self.connected_to_plc

    def apply_variables(self, values: Dict[str, Any]):
        if values["loading_failed"]: loading_state = "FAILED"
        elif values["loading_passed"]: loading_state = "PASSED"
        elif values["clip_station_working"] or values["tape_station_working"]: loading_state = "WORKING"
        else: loading_state = "WAITING"

        if values["unloading_failed"]: unloading_state = "FAILED"
        elif values["unloading_passed"]: unloading_state = "PASSED"
        elif values["clip_station_working"] or values["tape_station_working"]: unloading_state = "WORKING"
        else: unloading_state = "WAITING"

        self.load_box.set_state(loading_state)
        self.unload_box.set_state(unloading_state)

        table_mode = "SERVICE" if values["table_service"] else ("AUTO" if values["table_auto"] else "UNKNOWN")
        tape_mode = "SERVICE" if values["tape_service"] else ("AUTO" if values["tape_auto"] else "UNKNOWN")
        clip_mode = "SERVICE" if values["clip_service"] else ("AUTO" if values["clip_auto"] else "UNKNOWN")

        self.system_alarm = not bool(values.get("e_stop", True))

        # ROBOTS / STATIONS LOGIC
        robot1_state = bool(values.get("tape_robot_state", True))
        robot2_state = bool(values.get("clip_robot_state", True))
        robot3_state = bool(values.get("small_robot_state", True))

        station2_plc_working = bool(values.get("tape_station_working", False))
        station3_plc_working = bool(values.get("clip_station_working", False))

        station2_effective_working = station2_plc_working or robot1_state
        station3_effective_working = (
            station3_plc_working or robot2_state or robot3_state
        )

        self.robot1.set_state(robot1_state, tape_mode, self.system_alarm)
        self.robot2.set_state(robot2_state, clip_mode, self.system_alarm)
        self.robot3.set_state(robot3_state, clip_mode, self.system_alarm)

        self.status_st2.set_status(
            running=station2_effective_working,
            mode=tape_mode,
            alarm=self.system_alarm
        )
        self.status_st3.set_status(
            running=station3_effective_working,
            mode=clip_mode,
            alarm=self.system_alarm
        )

        self.turning_table.set_state(values["table_running"], table_mode, self.system_alarm)
        self.e_stop.set_state(self.system_alarm)

        both_stations_done = (
            not station2_effective_working
            and not station3_effective_working
        )
        e_stop_active = self.system_alarm

        self.cycle_timer.update_timer_state(
            both_stations_done=both_stations_done,
            table_running=bool(values["table_running"]),
            e_stop=e_stop_active,
        )

        self.tape_wall.set_tape_states(values.get("tape_states", []))

        self.detect_events(values)

        # Diagnostic des signaux contradictoires dans le DB620 avec variables corrigées
        conflict_now = (
            (not station2_plc_working and robot1_state) or
            (station2_plc_working and not robot1_state) or
            (not station3_plc_working and (robot2_state or robot3_state)) or
            (station3_plc_working and not (robot2_state or robot3_state))
        )
        previous_conflict = bool(self._last_values and self._last_values.get("_robot_station_conflict", False))

        if conflict_now and not previous_conflict:
            details = []
            if not station2_plc_working and robot1_state:
                details.append("ST2=STOPPED / ROBOT1=RUNNING")
            elif station2_plc_working and not robot1_state:
                details.append("ST2=WORKING / ROBOT1=STOPPED")
            if not station3_plc_working and (robot2_state or robot3_state):
                details.append("ST3=STOPPED / ROBOT2-3=RUNNING")
            elif station3_plc_working and not (robot2_state or robot3_state):
                details.append("ST3=WORKING / ROBOT2-3=STOPPED")
            self.log_event("PLC DIAGNOSTIC", "Incoherent DB620 signals: " + " | ".join(details))

        values_to_store = values.copy()
        values_to_store["_robot_station_conflict"] = conflict_now
        self._last_values = values_to_store

    def detect_events(self, values: Dict[str, Any]):
        previous = self._last_values
        if previous is None: return

        events = [
            ("loading_passed", "AI INIT", "Loading PASSED", "Loading validation cleared."),
            ("unloading_passed", "AI END", "Unloading PASSED", "Unloading validation cleared."),
            ("loading_failed", "AI INIT", "Loading FAILED", "Loading failure detected."),
            ("unloading_failed", "AI END", "Unloading FAILED", "Unloading failure detected."),
            ("e_stop", "SAFETY", "E-STOP", "Emergency stop active."),
            ("table_running", "TURN TABLE", "Table RUNNING", "Turning table rotation started."),
        ]

        for key, source, true_msg, false_msg in events:
            if bool(previous.get(key)) != bool(values.get(key)):
                if values.get(key): self.log_event("ALARM" if key in ("loading_failed", "unloading_failed", "e_stop") else source, true_msg)
                else: self.log_event(source, false_msg)

        mode_keys = ("table_auto", "table_service", "tape_auto", "tape_service", "clip_auto", "clip_service")
        if any(bool(previous.get(k)) != bool(values.get(k)) for k in mode_keys):
            self.log_event(
                "MODE", f"Table={('AUTO' if values['table_auto'] else 'SERVICE')}, "
                f"Tape={('AUTO' if values['tape_auto'] else 'SERVICE')}, Clip={('AUTO' if values['clip_auto'] else 'SERVICE')}"
            )

    def animate_graphics(self):
        self.status_st2.advance_animation()
        self.status_st3.advance_animation()
        self.e_stop.advance_animation()

        if self._last_values and self._last_values.get("table_running") and not self.system_alarm:
            self.rotation_angle = (self.rotation_angle + 3.5) % 360
            
        self.turning_table.set_angle(self.rotation_angle)

        tick = datetime.now().timestamp()
        
        # --- MODIFICATION POUR MOUVEMENT D'ESSUIE-GLACE ---
        # J'ai augmenté la vitesse (tick * 3.0) et l'angle max d'amplitude envoyé (35) pour tous les bras au travail
        self.robot1.set_angle(math.sin(tick * 3.0) * 35 if self.robot1.running and self.robot1.state == "WORKING" else 0)
        self.robot2.set_angle(math.cos(tick * 2.8) * 35 if self.robot2.running and self.robot2.state == "WORKING" else 0)
        self.robot3.set_angle(math.sin(tick * 2.5) * 30 if self.robot3.running and self.robot3.state == "WORKING" else 0)
        # --------------------------------------------------

    def update_clock(self):
        now = datetime.now()
        self.clock.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%d/%m/%Y"))

    def closeEvent(self, event):
        try:
            if self.plc_thread.isRunning():
                self.plc_worker.stopRequested.emit()
                self.plc_thread.quit()
                self.plc_thread.wait(3000)
        except Exception:
            pass
        try:
            if self.db_conn is not None:
                self.db_conn.close()
        except Exception:
            pass
        event.accept()

def main():
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SMCSupervisionDashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()