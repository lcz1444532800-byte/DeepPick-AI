from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPen, QPixmap


def red_cursor(text=False):
    pixmap = QPixmap(64, 64)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    segments = (((16, 6), (16, 26)), ((12, 6), (20, 6)), ((12, 26), (20, 26))) if text else (
        ((16, 4), (16, 12)), ((16, 20), (16, 28)), ((4, 16), (12, 16)), ((20, 16), (28, 16)))
    for color, width in (("#ffffff", 4), ("#e33838", 2)):
        painter.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for first, last in segments:
            painter.drawLine(QPointF(*first), QPointF(*last))
    if not text:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e33838"))
        painter.drawEllipse(QPointF(16, 16), 1.6, 1.6)
    painter.end()
    return QCursor(pixmap, 16, 16)
