from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .cursors import red_cursor


@dataclass
class Capture:
    image: QImage
    rect: QRect
    scale: float


class CaptureWindow(QWidget):
    captured = Signal(object)
    cancelled = Signal()

    def __init__(self, cancel_key="Esc"):
        super().__init__()
        self.setWindowTitle("DeepPick AI · Capture")
        self.cancel_key = cancel_key
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setCursor(red_cursor())
        self.bounds = QRect()
        screens = QGuiApplication.screens()
        for screen in screens:
            self.bounds = self.bounds.united(screen.geometry())
        self.scale = max(s.devicePixelRatio() for s in screens)
        if self.bounds.width()*self.bounds.height()*self.scale**2 > 60_000_000:
            raise RuntimeError("The desktop is too large. Temporarily disconnect a display.")
        self.shots = []
        self.image = QImage()
        painter = None
        if len(screens) > 1:
            self.image = QImage(round(self.bounds.width()*self.scale), round(self.bounds.height()*self.scale),
                                QImage.Format.Format_RGB32)
            self.image.fill(QColor("#101521"))
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for screen in screens:
            g = screen.geometry()
            shot = screen.grabWindow(0)
            if shot.isNull():
                if painter:
                    painter.end()
                raise RuntimeError("Could not read the screen. Check remote desktop or capture permissions.")
            self.shots.append((g, shot.toImage(), screen.devicePixelRatio()))
            target = QRectF((g.x()-self.bounds.x())*self.scale, (g.y()-self.bounds.y())*self.scale,
                            g.width()*self.scale, g.height()*self.scale)
            if painter:
                painter.drawPixmap(target, shot, QRectF(0, 0, shot.width(), shot.height()))
            else:
                self.image = QImage(self.shots[-1][1])
        if painter:
            painter.end()
        self.image.setDevicePixelRatio(self.scale)
        self.setGeometry(self.bounds)
        self.anchor = None
        self.end = None
        self.done = False

    def open(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def region(self):
        if self.anchor is None or self.end is None:
            return QRect()
        return QRect(self.anchor, self.end).normalized().intersected(self.rect())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawImage(QPointF(0, 0), self.image)
        rect = self.region()
        # One fixed image. Moving the selection only changes the dimming mask.
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        if not rect.isEmpty():
            hole = QPainterPath()
            hole.addRect(QRectF(rect))
            shade = shade.subtracted(hole)
        p.fillPath(shade, QColor(9, 15, 29, 135))
        if not rect.isEmpty():
            p.setPen(QPen(QColor("#e33838"), 2))
            p.drawRect(rect.adjusted(0, 0, -1, -1))
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        top = screen.geometry().topLeft()-self.bounds.topLeft()
        hint = QRect(top.x()+30, top.y()+30, 480, 36)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(hint, 8, 8)
        p.setPen(QColor("#202833"))
        dimensions = f"   {round(rect.width()*self.scale)} × {round(rect.height()*self.scale)}" if not rect.isEmpty() else ""
        p.drawText(hint, Qt.AlignmentFlag.AlignCenter, f"Drag to capture · {self.cancel_key} to cancel{dimensions}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.anchor = event.position().toPoint()
            self.end = self.anchor
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self.anchor is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.anchor is None:
            return
        self.end = event.position().toPoint()
        rect = self.region()
        if rect.width() < 8 or rect.height() < 8:
            self.anchor = self.end = None
            self.update()
            return
        crop = QRect(round(rect.x()*self.scale), round(rect.y()*self.scale),
                     round(rect.width()*self.scale), round(rect.height()*self.scale))
        global_rect = rect.translated(self.bounds.topLeft())
        result = None
        # Preserve native pixels on each monitor, even with mixed DPI settings.
        for geometry, shot, scale in self.shots:
            if geometry.contains(global_rect):
                local = global_rect.translated(-geometry.topLeft())
                native = QRect(round(local.x()*scale), round(local.y()*scale),
                               round(local.width()*scale), round(local.height()*scale))
                result = Capture(shot.copy(native), global_rect, scale)
                break
        if result is None:
            result = Capture(self.image.copy(crop), global_rect, self.scale)
        self.done = True
        self.close()
        self.captured.emit(result)

    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeySequence
        if event.key() == Qt.Key.Key_Escape or QKeySequence(event.keyCombination()).toString() == self.cancel_key:
            self.close()

    def closeEvent(self, event):
        if not self.done:
            self.cancelled.emit()
        event.accept()
