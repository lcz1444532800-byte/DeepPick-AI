"""Lightweight dot field drawn over the original pixels."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient


class DotField:
    def __init__(self, width, height):
        self.bounds = QRectF(0, 0, width, height)
        step = max(18, math.sqrt(width * height / 1200))
        self.dots = []
        row = 0
        y = step / 2
        while y < height:
            column = 0
            x = step / 2
            while x < width:
                phase = (column * .79 + row * 1.17) % (math.pi * 2)
                color = (column + row * 2) % 3
                self.dots.append((QPointF(x, y), phase, color))
                column += 1
                x += step
            row += 1
            y += step

    def paint(self, painter, seconds):
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        gradient = QLinearGradient(self.bounds.topLeft(), self.bounds.bottomRight())
        gradient.setColorAt(0, QColor(178, 206, 255, 24))
        gradient.setColorAt(.5, QColor(227, 214, 255, 18))
        gradient.setColorAt(1, QColor(188, 242, 229, 24))
        painter.fillRect(self.bounds, gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        palette = ((84, 113, 229), (153, 106, 208), (60, 157, 151))
        for point, phase, color in self.dots:
            wave = .5 + .5 * math.sin(seconds * 2.3 + phase + .65 * math.sin(seconds * .8 + point.y() * .018))
            radius = .65 + 2.65 * wave ** 1.6
            painter.setBrush(QColor(*palette[color], round(38 + 104 * wave)))
            painter.drawEllipse(point, radius, radius)
        painter.restore()
