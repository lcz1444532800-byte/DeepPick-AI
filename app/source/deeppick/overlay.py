from __future__ import annotations

import ctypes
from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .cursors import red_cursor
from .domain import Selection
from .effects import DotField
from .selection_mapping import remap_selection


class OverlayToolbar(QWidget):
    def __init__(self, overlay):
        super().__init__()
        self.setWindowTitle("DeepPick AI · Text actions")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("OverlayToolbar")
        self.setStyleSheet("#OverlayToolbar{background:white;border:1px solid #dce2e9;border-radius:10px;} QLabel{color:#667080;padding:0 4px;} QLabel#RecognitionState{color:#3f65c4;font-size:12px;} QPushButton{background:white;color:#263343;border:0;border-radius:6px;padding:7px 9px;} QPushButton:hover{background:#eef2f7;} QPushButton:disabled{color:#aab1bc;}")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(3)
        self.state = QLabel("Recognizing…")
        self.state.setObjectName("RecognitionState")
        self.state.setMinimumWidth(200)
        row.addWidget(self.state)
        self.status = QLabel("")
        self.status.setMinimumWidth(70)
        row.addWidget(self.status)
        self.buttons = {}
        for name, text, action in (("all", "Select all", overlay.select_all), ("clear", "Clear", overlay.clear_selection),
                                   ("copy", "Copy", overlay.copy_selected), ("ai", "AI enhance", overlay.request_ai),
                                   ("result", "View text", overlay.request_result), ("close", "×", overlay.close)):
            item = QPushButton(text)
            item.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            item.clicked.connect(action)
            self.buttons[name] = item
            row.addWidget(item)
        self.ai_button = self.buttons['ai']
        self.ai_button.setToolTip("Enhance manually" if overlay.settings.api_key else "Add an API key in Settings first")
        self.adjustSize()

    def refresh(self, overlay):
        for name, item in self.buttons.items():
            item.setEnabled(name == 'close' or (overlay.ready and (name != 'ai' or
                            (bool(overlay.settings.api_key) and not overlay.ai_busy))))
        self.ai_button.setText("Enhancing…" if overlay.ai_busy else "AI enhance")
        self.state.setText(overlay.state_text)
        self.state.setStyleSheet("color:#16786a;" if overlay.ai_used else "color:#3f65c4;")
        self.status.setText(f"{len(overlay.selection.indices)} chars" if overlay.selection.indices else "")


class TextOverlay(QWidget):
    copied = Signal(str)
    closed = Signal()
    enhance = Signal()
    result_requested = Signal()

    def __init__(self, capture, blocks, settings):
        super().__init__()
        self.setWindowTitle("DeepPick AI · Select text")
        self.capture, self.settings = capture, settings
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setGeometry(capture.rect)
        self.background = QImage(capture.image)
        self.background.setDevicePixelRatio(capture.scale)
        self.selection = Selection([])
        self.ready = False
        self.ai_busy = self.ai_used = False
        self.state_text = "Recognizing…"
        self.anchor = self.drag_origin = self.drag_last = None
        self.pending_drags = []
        self.cells, self.lines = [], []
        self.highlight = QPainterPath()
        self.text_areas = QPainterPath()
        self.dim_areas = QPainterPath()
        self.dots = DotField(self.width(), self.height())
        self.elapsed = QElapsedTimer()
        self.elapsed.start()
        self.animation = QTimer(self)
        self.animation.setInterval(33)
        self.animation.timeout.connect(self.update)
        self.toolbar = OverlayToolbar(self)
        self.toolbar.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.keyboard = QTimer(self)
        self.keyboard.setInterval(16)
        self.keyboard.timeout.connect(self._poll_keys)
        self.previous_keys = {}
        self.keyboard.start()
        if blocks is not None:
            self.set_blocks(blocks)
        else:
            self.set_processing()

    def set_processing(self, text="Recognizing…"):
        self.state_text = text
        self.setCursor(red_cursor())
        self.toolbar.refresh(self)
        self.animation.start()
        self.update()

    def set_blocks(self, blocks, ai_used=False, preserve_selection=False):
        previous = self.selection
        self.selection = Selection(blocks)
        if preserve_selection:
            self.selection.committed = remap_selection(previous, self.selection)
        self.ready = True
        self.ai_used = ai_used
        self.ai_busy = False
        self.state_text = "Done · AI enhanced" if ai_used else "Done · Local OCR"
        self.setCursor(red_cursor(text=True))
        self._layout_text()
        for first, last in self.pending_drags:
            a, b = self.hit(first, nearest=True), self.hit(last, nearest=True)
            if a is not None and b is not None:
                self.selection.range(a, b)
                self.selection.commit()
        self.pending_drags.clear()
        if self.drag_origin is not None:
            self.anchor = self.hit(self.drag_origin, nearest=True)
            last = self.hit(self.drag_last or self.drag_origin, nearest=True)
            if self.anchor is not None and last is not None:
                self.selection.range(self.anchor, last)
        self.animation.stop()
        self._update_selection()

    def _layout_text(self):
        self.cells, self.lines = [], []
        areas = QPainterPath()
        areas.setFillRule(Qt.FillRule.WindingFill)
        scale = self.capture.scale
        for block, offset in zip(self.selection.blocks, self.selection.offsets):
            font = QFont("Microsoft YaHei UI")
            font.setPixelSize(max(8, round(block.height / scale * .78)))
            metrics = QFontMetricsF(font)
            weights = [max(1, metrics.horizontalAdvance(char)) for char in block.text]
            total = sum(weights)
            if block.polygon:
                tl, tr, br, bl = [QPointF(x / scale, y / scale) for x, y in block.polygon]
            else:
                x, y, w, h = block.x / scale, block.y / scale, block.width / scale, block.height / scale
                tl, tr, br, bl = QPointF(x,y), QPointF(x+w,y), QPointF(x+w,y+h), QPointF(x,y+h)
            part = QPainterPath()
            part.addPolygon(QPolygonF([tl, tr, br, bl]))
            part.closeSubpath()
            areas.addPath(part)
            fraction = 0.
            line = []
            for index, weight in enumerate(weights):
                following = fraction + weight / total
                polygon = QPolygonF([tl+(tr-tl)*fraction, tl+(tr-tl)*following,
                                     bl+(br-bl)*following, bl+(br-bl)*fraction])
                cell = (offset+index, polygon)
                self.cells.append(cell)
                line.append(cell)
                fraction = following
            self.lines.append(line)
        stroker = QPainterPathStroker()
        stroker.setWidth(5)
        self.text_areas = areas.united(stroker.createStroke(areas)).simplified()
        full = QPainterPath()
        full.addRect(QRectF(self.rect()))
        self.dim_areas = full.subtracted(self.text_areas)

    def open(self):
        self.show()
        screen = QGuiApplication.screenAt(self.capture.rect.center()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        width = min(self.toolbar.sizeHint().width(), area.width()-20)
        self.toolbar.resize(width, self.toolbar.sizeHint().height())
        x = max(area.x()+10, min(self.capture.rect.center().x()-width//2, area.right()-width-10))
        y = self.capture.rect.bottom()+12
        if y+self.toolbar.height() > area.bottom():
            y = max(area.y()+10, self.capture.rect.top()-self.toolbar.height()-12)
        self.toolbar.move(x,y)
        self.toolbar.show()
        self.raise_()
        self.toolbar.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.repaint()

    def hit(self, point, nearest=False):
        nearby = []
        for index, polygon in self.cells:
            if polygon.containsPoint(point, Qt.FillRule.OddEvenFill):
                return index
            if polygon.boundingRect().adjusted(-5,-5,5,5).contains(point):
                nearby.append((index, polygon))
        candidates = nearby or (self.cells if nearest else [])
        if candidates:
            return min(candidates, key=lambda cell:(cell[1].boundingRect().center()-point).manhattanLength())[0]
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(QPointF(0,0), self.background)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.ready:
            painter.fillPath(self.dim_areas, QColor(12,20,34,126))
            if not self.highlight.isEmpty():
                painter.save()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                painter.fillPath(self.highlight, QColor(255,213,45,190))
                painter.restore()
        if not self.ready or self.ai_busy:
            self.dots.paint(painter, self.elapsed.elapsed()/1000)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor('#5c7dde') if not self.ready or self.ai_busy else QColor('#93a8ce'), 1.5))
        painter.drawRect(QRectF(self.rect()).adjusted(.75,.75,-.75,-.75))
        if not self.ready and self.drag_origin is not None and self.drag_last is not None:
            painter.setPen(QPen(QColor('#f0c632'), 2))
            painter.drawLine(self.drag_origin, self.drag_last)

    def _update_selection(self):
        chosen = self.selection.indices
        path = QPainterPath()
        for line in self.lines:
            run = []
            def append_run():
                if run:
                    first, last = run[0], run[-1]
                    part = QPainterPath()
                    part.addPolygon(QPolygonF([first[0],last[1],last[2],first[3]]))
                    part.closeSubpath()
                    path.addPath(part)
            for index, polygon in line:
                if index in chosen: run.append(polygon)
                else:
                    append_run()
                    run = []
            append_run()
        self.highlight = path
        self.toolbar.refresh(self)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            return
        if event.button() != Qt.MouseButton.LeftButton: return
        self.drag_origin = QPointF(event.position())
        self.drag_last = self.drag_origin
        self.anchor = self.hit(self.drag_origin) if self.ready else None
        if self.anchor is not None:
            self.selection.range(self.anchor,self.anchor)
        self.grabMouse()
        self._update_selection()

    def mouseMoveEvent(self, event):
        if self.drag_origin is None: return
        self.drag_last = QPointF(event.position())
        if self.ready and self.anchor is not None:
            last = self.hit(self.drag_last, nearest=True)
            if last is not None: self.selection.range(self.anchor,last)
            self._update_selection()
        else: self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.drag_origin is None: return
        if self.ready and self.anchor is not None:
            last = self.hit(event.position(), nearest=True)
            if last is not None: self.selection.range(self.anchor,last)
            self.selection.commit()
        elif not self.ready:
            self.pending_drags.append((self.drag_origin,QPointF(event.position())))
            self.pending_drags = self.pending_drags[-16:]
        self.anchor = self.drag_origin = self.drag_last = None
        self.releaseMouse()
        self._update_selection()

    def _key_down(self, sequence):
        user = ctypes.windll.user32
        if sequence in ('Esc','Escape'): return bool(user.GetAsyncKeyState(0x1B)&0x8000)
        from .win32 import hotkey_parts
        try:
            mods,key = hotkey_parts(sequence)
            return bool(user.GetAsyncKeyState(key)&0x8000) and all(
                bool(user.GetAsyncKeyState(vk)&0x8000) for flag,vk in ((2,0x11),(1,0x12),(4,0x10),(8,0x5B)) if mods&flag)
        except ValueError: return False

    def _poll_keys(self):
        for name, sequence, action in (("copy",self.settings.copy_key,self.copy_selected),
                                      ("cancel",self.settings.cancel_key,self.close), ("all","Ctrl+A",self.select_all)):
            down = self._key_down(sequence)
            if down and not self.previous_keys.get(name,False):
                action()
                if name in ('copy','cancel') and not self.isVisible(): return
            self.previous_keys[name] = down

    def select_all(self):
        if not self.ready: return
        self.selection.committed = set(range(self.selection.length))
        self.selection.preview.clear()
        self._update_selection()

    def clear_selection(self):
        self.selection.clear()
        self.pending_drags.clear()
        self._update_selection()

    def copy_selected(self):
        if not self.ready: return
        text = self.selection.text()
        if text:
            self.copied.emit(text)
            self.close()
        else: self.toolbar.status.setText("Select text")

    def request_result(self):
        if self.ready: self.result_requested.emit()

    def request_ai(self):
        if self.ready and not self.ai_busy: self.enhance.emit()

    def set_ai_busy(self, busy):
        self.ai_busy = busy
        if busy:
            self.state_text = "Enhancing with AI…"
            self.animation.start()
        else:
            if self.ready:
                self.animation.stop()
                if self.state_text == 'Enhancing with AI…':
                    self.state_text = "Done · AI enhanced" if self.ai_used else "Done · Local OCR"
        self.toolbar.refresh(self)
        self.update()

    def mark_ai_failed(self, canceled=False):
        self.set_ai_busy(False)
        result = 'Enhanced result' if self.ai_used else 'Local result'
        self.state_text = ('AI canceled · ' if canceled else 'AI failed · ') + result
        self.toolbar.refresh(self)

    def closeEvent(self, event):
        self.animation.stop()
        self.keyboard.stop()
        if self.drag_origin is not None: self.releaseMouse()
        self.toolbar.close()
        self.closed.emit()
        event.accept()
