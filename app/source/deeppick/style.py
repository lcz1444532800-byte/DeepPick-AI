from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


STYLE = """
QWidget { font-family:'Microsoft YaHei UI','Segoe UI'; font-size:14px; color:#202833; }
QMainWindow,QDialog { background:#ffffff; }
QLabel#Title { font-size:32px; font-weight:600; color:#171e28; }
QLabel#Subtitle { color:#5d6876; font-size:15px; }
QLabel#Muted { color:#7b8490; font-size:12px; }
QLabel#Status { color:#697583; font-size:13px; }
QLabel#Shortcut { color:#929aa5; font-size:22px; padding-bottom:2px; }
QFrame#Guide { background:#f7f8fa; border:1px solid #eef0f3; border-radius:18px; }
QLabel#GuideTitle { font-size:18px; font-weight:600; }
QLabel#StepNumber { font-size:12px; color:#929aa5; min-width:24px; }
QLabel#Key { background:white; border:1px solid #e1e5ea; border-radius:6px; padding:4px 9px; font-size:12px; color:#637083; }
QPushButton { background:white; border:1px solid #dfe4ea; border-radius:10px; padding:10px 18px; }
QPushButton:hover { background:#f5f7fa; border-color:#bbc5d2; }
QPushButton:pressed { background:#e9edf2; }
QPushButton:disabled { color:#a3aab4; background:#f4f5f7; border-color:#e7eaee; }
QPushButton#Primary { background:#202a37; color:white; font-weight:600; border:0; padding:16px 24px; font-size:17px; }
QPushButton#Primary:hover { background:#344153; }
QPushButton#Primary:disabled { background:#a6aeb8; }
QPushButton#Quiet { border:0; background:transparent; color:#5d6876; padding:9px 15px; }
QPushButton#Quiet:hover { background:#f5f7fa; }
QLineEdit,QKeySequenceEdit,QComboBox,QDoubleSpinBox { background:#fbfcfd; border:1px solid #dce2e9; border-radius:8px; padding:9px; }
QLineEdit:focus,QKeySequenceEdit:focus,QComboBox:focus { border-color:#72859d; }
QPlainTextEdit,QListWidget { background:white; border:1px solid #e0e5eb; border-radius:9px; padding:8px; selection-background-color:#d3e4ff; selection-color:#202833; }
QListWidget::item { padding:12px; border-bottom:1px solid #eef0f3; }
QListWidget::item:selected { background:#e9f1ff; }
QCheckBox { spacing:10px; }
QTabWidget::pane { border:0; }
QTabBar::tab { background:white; color:#8b94a0; padding:10px 24px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#202a37; border-bottom-color:#202a37; }
QScrollArea { border:0; background:transparent; }
QToolTip { background:white; color:#202833; border:1px solid #dce2e9; padding:6px; }
QMenu { background:white; color:#202833; border:1px solid #dce2e9; padding:5px; }
QMenu::item { padding:8px 24px; }
QMenu::item:selected { background:#edf2f8; }

"""


def application_icon():
    pixmap = QPixmap(256,256)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#10243b"))
    p.drawRoundedRect(QRectF(8,8,240,240),52,52)
    p.setPen(QPen(QColor("#64e8ce"),12,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    for a,b,c in (((62,92),(62,60),(94,60)),((162,60),(194,60),(194,92)),
                   ((62,164),(62,196),(94,196)),((162,196),(194,196),(194,164))):
        p.drawLine(QPointF(*a),QPointF(*b)); p.drawLine(QPointF(*b),QPointF(*c))
    p.setPen(QPen(QColor("#e8f7ff"),10,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(91,101),QPointF(165,101))
    p.drawLine(QPointF(91,128),QPointF(155,128))
    p.drawLine(QPointF(91,155),QPointF(135,155))
    p.end()
    return QIcon(pixmap)
