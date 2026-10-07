from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor, QKeySequence, QPalette, QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QFrame, QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)



def label(text, name="", wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, action, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(action)
    if primary:
        widget.setObjectName("Primary")
    return widget


class MainWindow(QMainWindow):
    capture_requested = Signal()
    settings_requested = Signal()
    history_requested = Signal()
    result_requested = Signal()
    auto_enhance_changed = Signal(bool)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self.exiting = False
        self.setWindowTitle("DeepPick AI")
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window,QColor('white'))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setMinimumSize(760, 470)
        self.resize(1040, 643)
        central = QWidget()
        central.setPalette(palette)
        central.setAutoFillBackground(True)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(48, 36, 48, 26)
        layout.setSpacing(24)
        header = QHBoxLayout()
        header.addWidget(label("DeepPick AI", "Title"))
        header.addStretch()
        for title, action in (("History", self.history_requested.emit), ("Settings", self.settings_requested.emit)):
            item = button(title, action)
            item.setObjectName("Quiet")
            header.addWidget(item)
        layout.addLayout(header)
        layout.addStretch(1)
        body = QHBoxLayout()
        body.setSpacing(60)
        capture_column = QVBoxLayout()
        capture_column.setSpacing(18)
        capture_column.addStretch()
        self.shortcut = label("Ctrl + Space", "Shortcut")
        capture_column.addWidget(self.shortcut)
        self.capture_button = button("Capture", self.capture_requested.emit, True)
        self.capture_button.setMinimumHeight(60)
        capture_column.addWidget(self.capture_button)
        self.enhance = QCheckBox("Auto enhance · Optional")
        self.enhance.toggled.connect(self.auto_enhance_changed.emit)
        capture_column.addWidget(self.enhance)
        self.api = label("API key not configured", "Muted")
        capture_column.addWidget(self.api)
        self.state = label("", "Status", True)
        self.state.hide()
        capture_column.addWidget(self.state)
        capture_column.addStretch()
        body.addLayout(capture_column, 5)
        guide = QFrame()
        guide.setObjectName("Guide")
        guide_layout = QVBoxLayout(guide)
        guide_layout.setContentsMargins(30, 28, 30, 28)
        guide_layout.setSpacing(20)
        guide_layout.addWidget(label("Quick guide", "GuideTitle"))
        self.guide_keys = []
        for number, text, key in (("01", "Capture an area", "Ctrl + Space"),
                                  ("02", "Drag to select; repeat to add", ""),
                                  ("03", "Copy selected text", "Ctrl + Enter")):
            row = QVBoxLayout()
            line = QHBoxLayout()
            line.addWidget(label(number, "StepNumber"))
            line.addWidget(label(text, wrap=True), 1)
            row.addLayout(line)
            if key:
                key_row = QHBoxLayout()
                key_row.addSpacing(30)
                item = label(key, "Key")
                self.guide_keys.append(item)
                key_row.addWidget(item)
                key_row.addStretch()
                row.addLayout(key_row)
            guide_layout.addLayout(row)
        self.cancel_hint = label("Esc or right-click to close", "Muted")
        guide_layout.addWidget(self.cancel_hint)
        full_guide = button("User guide / FAQ", self.open_guide)
        full_guide.setObjectName("Quiet")
        guide_layout.addWidget(full_guide)
        body.addWidget(guide, 6)
        layout.addLayout(body, 6)
        layout.addStretch(1)
        credit = label('<a href="about" style="color:#7b8490;text-decoration:none">Developer:Chunze Liu</a>', "Muted")
        credit.linkActivated.connect(self.about)
        layout.addWidget(credit)

    def open_guide(self):
        guide = self.paths.root / "User-Guide.html"
        if not guide.is_file() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(guide))):
            QMessageBox.information(self, "Quick guide", "Open User-Guide.html in the application folder.")

    def about(self):
        QMessageBox.information(self, "DeepPick AI", "DeepPick AI 1.2.3\nDeveloper:Chunze Liu")

    def set_status(self, text):
        self.state.setText(text)
        self.state.setVisible(bool(text))

    def refresh(self, settings):
        def key(text):
            return text.replace("Return", "Enter").replace("+", " + ")
        self.shortcut.setText(key(settings.capture_key))
        self.guide_keys[0].setText(key(settings.capture_key))
        self.guide_keys[1].setText(key(settings.copy_key))
        self.cancel_hint.setText(f"{key(settings.cancel_key)} or right-click to close")
        self.enhance.blockSignals(True)
        self.enhance.setChecked(settings.auto_enhance)
        self.enhance.blockSignals(False)
        self.api.setText("" if settings.api_key else "API key not configured")
        self.api.setVisible(settings.auto_enhance and not settings.api_key)

    def closeEvent(self, event):
        if self.exiting:
            event.accept()
        else:
            self.hide()
            event.ignore()


class SettingsDialog(QDialog):
    save_requested = Signal(object)
    test_requested = Signal(str)
    clear_cache_requested = Signal()

    def __init__(self, settings, startup_path, parent=None):
        super().__init__(parent)
        self.original = settings
        self.setWindowTitle("DeepPick AI · Settings")
        self.resize(720, 510)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        recognition = QWidget()
        form = QVBoxLayout(recognition)
        form.setContentsMargins(4, 24, 4, 12)
        form.setSpacing(18)
        row = QFormLayout()
        row.setSpacing(18)
        self.api_key = QLineEdit(settings.api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("DeepSeek API Key")
        self.api_key.setMaxLength(1000)
        row.addRow("API Key", self.api_key)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(.1, 1.)
        self.threshold.setSingleStep(.05)
        self.threshold.setValue(settings.threshold)
        row.addRow("Enhancement threshold", self.threshold)
        form.addLayout(row)
        self.test_button = button("Test connection", self._test)
        form.addWidget(self.test_button)
        self.test_status = label("", "Muted", True)
        form.addWidget(self.test_status)
        form.addStretch()
        form.addWidget(label("AI uploads this capture.", "Muted"))
        tabs.addTab(recognition, "DeepSeek")
        keys = QWidget()
        key_layout = QVBoxLayout(keys)
        key_layout.setContentsMargins(4, 24, 4, 12)
        key_form = QFormLayout()
        key_form.setSpacing(18)
        self.capture_key = QKeySequenceEdit(QKeySequence(settings.capture_key))
        self.copy_key = QKeySequenceEdit(QKeySequence(settings.copy_key))
        self.cancel_key = QKeySequenceEdit(QKeySequence(settings.cancel_key))
        for editor in (self.capture_key, self.copy_key, self.cancel_key):
            editor.setMaximumSequenceLength(1)
        key_form.addRow("Capture", self.capture_key)
        key_form.addRow("Copy text", self.copy_key)
        key_form.addRow("Close", self.cancel_key)
        key_layout.addLayout(key_form)
        key_layout.addWidget(button("Restore defaults", self._reset_keys))
        key_layout.addStretch()
        tabs.addTab(keys, "Shortcuts")
        general = QWidget()
        general_layout = QVBoxLayout(general)
        general_layout.setContentsMargins(4, 24, 4, 12)
        general_layout.setSpacing(24)
        self.history = QCheckBox("Save the last 20 results")
        self.history.setChecked(settings.history_enabled)
        self.hidden = QCheckBox("Start in the background")
        self.hidden.setChecked(settings.start_hidden)
        self.autostart = QCheckBox("Start with Windows")
        self.autostart.setChecked(settings.autostart)
        for item in (self.history, self.hidden, self.autostart):
            general_layout.addWidget(item)
        general_layout.addStretch()
        tabs.addTab(general, "General")
        storage = QWidget()
        storage_layout = QVBoxLayout(storage)
        storage_layout.setContentsMargins(4, 24, 4, 12)
        storage_layout.setSpacing(20)
        storage_form = QFormLayout()
        self.cache_limit = QSpinBox()
        self.cache_limit.setRange(32, 4096)
        self.cache_limit.setSuffix(" MB")
        self.cache_limit.setValue(settings.cache_limit_mb)
        storage_form.addRow("Cache limit (including temporary files)", self.cache_limit)
        storage_layout.addLayout(storage_form)
        self.storage_usage = label("Calculating…", "Muted", True)
        storage_layout.addWidget(self.storage_usage)
        self.clear_cache_button = button("Clear cache", self.clear_cache_requested.emit)
        storage_layout.addWidget(self.clear_cache_button)
        storage_layout.addStretch()
        storage_layout.addWidget(label("Clean every 5 min · Cache expires after 7 days · Logs: 50 MB max", "Muted", True))
        tabs.addTab(storage, "Storage")
        self.error = label("", "Status", True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _test(self):
        if not self.api_key.text().strip():
            self.test_status.setText("Enter an API key")
            return
        self.test_button.setEnabled(False)
        self.test_status.setText("Connecting…")
        self.test_requested.emit(self.api_key.text().strip())

    def test_finished(self, text):
        self.test_button.setEnabled(True)
        self.test_status.setText(text)

    def _reset_keys(self):
        for editor, sequence in ((self.capture_key, "Ctrl+Space"), (self.copy_key, "Ctrl+Return"), (self.cancel_key, "Esc")):
            editor.setKeySequence(QKeySequence(sequence))

    def _save(self):
        def text(editor):
            return editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        settings = replace(self.original, api_key=self.api_key.text().strip(), threshold=self.threshold.value(),
                           capture_key=text(self.capture_key), copy_key=text(self.copy_key), cancel_key=text(self.cancel_key),
                           history_enabled=self.history.isChecked(), start_hidden=self.hidden.isChecked(),
                           autostart=self.autostart.isChecked(), cache_limit_mb=self.cache_limit.value())
        self.save_requested.emit(settings)


class HistoryDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("DeepPick AI · History")
        self.resize(720,590)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Last 20 results","Subtitle"))
        self.list = QListWidget()
        self.list.setMaximumHeight(210)
        layout.addWidget(self.list)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        actions = QHBoxLayout()
        actions.addWidget(button("Copy text",self.copy))
        actions.addWidget(button("Delete selected",self.remove))
        actions.addStretch()
        actions.addWidget(button("Clear history",self.clear))
        layout.addLayout(actions)
        self.list.currentRowChanged.connect(self.select)
        self.refresh()

    def refresh(self):
        self.records = self.store.load()
        self.list.clear()
        for record in self.records:
            preview = str(record.get("text",""))[:45].replace("\n"," ")
            self.list.addItem(f"{record.get('time','')}   {preview}")
        if self.records:
            self.list.setCurrentRow(0)
        else:
            self.text.setPlainText("No saved results")

    def select(self,row):
        if 0 <= row < len(self.records):
            self.text.setPlainText(self.records[row].get("text",""))

    def copy(self):
        from PySide6.QtWidgets import QApplication
        if self.records and self.list.currentRow() >= 0:
            QApplication.clipboard().setText(self.text.toPlainText())

    def remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.records):
            self.records.pop(row)
            self.store.replace(self.records)
            self.refresh()

    def clear(self):
        if self.records and QMessageBox.question(self,"Clear history","Delete all saved recognition results?") == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self.refresh()


class ResultDialog(QDialog):
    ai_requested = Signal(str)
    overlay_requested = Signal()

    def __init__(self,text,blocks,ai_enabled,parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepPick AI · Results")
        self.resize(1040,650)
        layout = QVBoxLayout(self)
        self.heading = label("Recognized text","Subtitle")
        layout.addWidget(self.heading)
        self.text = QPlainTextEdit(text)
        layout.addWidget(self.text)
        tasks = QHBoxLayout()
        self.ai_buttons = []
        for title,task in (("AI correct","enhance"),("Restore table","table"),("Improve formulas","formula"),
                            ("Translate","translate"),("Summarize","summary"),("Explain","explain")):
            widget = button(title,lambda checked=False,t=task:self.ai_requested.emit(t))
            widget.setEnabled(ai_enabled)
            self.ai_buttons.append(widget)
            tasks.addWidget(widget)
        layout.addLayout(tasks)
        self.note = label("AI uploads this capture." if ai_enabled else "Add an API key in Settings.","Muted",True)
        layout.addWidget(self.note)
        actions = QHBoxLayout()
        actions.addWidget(button("Back to selection",self.overlay_requested.emit))
        actions.addStretch()
        actions.addWidget(button("Copy all",self.copy,True))
        actions.addWidget(button("Export text",self.export))
        layout.addLayout(actions)

    def set_ai_enabled(self, enabled):
        for item in self.ai_buttons:
            item.setEnabled(enabled)
        self.note.setText("AI uploads this capture." if enabled else "Add an API key in Settings.")

    def copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text.toPlainText())
        self.note.setText("Copied")

    def export(self):
        from PySide6.QtWidgets import QInputDialog
        from .storage import atomic_write
        import time
        name, accepted = QInputDialog.getText(self,"Export text","Filename (saved in D:\\DeepPickAI\\output):",
                                             text="Recognized-text-"+time.strftime("%Y%m%d-%H%M%S")+".txt")
        if not accepted or not name.strip():
            return
        name = name.strip()
        if any(c in name for c in '<>:"/\\|?*') or name in (".","..") or name.endswith(("."," ")):
            QMessageBox.warning(self,"Invalid filename","Enter a filename without a path or special characters.")
            return
        if not name.lower().endswith(".txt"):
            name += ".txt"
        target = Path("D:/DeepPickAI/output")/name
        if target.exists() and QMessageBox.question(self,"Replace file","This file already exists. Replace it?") != QMessageBox.StandardButton.Yes:
            return
        try:
            atomic_write(target,self.text.toPlainText().encode("utf-8-sig"))
            self.note.setText("Exported")
        except OSError:
            QMessageBox.warning(self,"Export failed","Check folder permissions and free disk space.")
