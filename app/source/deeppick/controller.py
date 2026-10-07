from __future__ import annotations

import logging
from dataclasses import replace

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .ai_service import AiJob
from .capture import CaptureWindow
from .domain import all_text, should_enhance
from .ocr_service import OcrService
from .overlay import TextOverlay
from .storage import ConfigStore, HistoryStore, cleanup
from .screen_sync import hide_capture_sources, restore_capture_sources, flush_desktop
from .ui import HistoryDialog, MainWindow, ResultDialog, SettingsDialog
from .win32 import GlobalHotkey, apply_autostart, hotkey_parts


class ApiCheck(QThread):
    result = Signal(str)

    def __init__(self, key):
        super().__init__()
        self.key = key

    def run(self):
        import httpx
        try:
            with httpx.Client(timeout=15,follow_redirects=False) as client:
                response = client.get("https://api.deepseek.com/models",headers={"Authorization":"Bearer "+self.key})
                if response.status_code == 200:
                    names = {m["id"] for m in response.json().get("data",[])}
                    self.result.emit("Connected" if "deepseek-flash" in names else "Connected. The image model is currently unavailable.")
                elif response.status_code == 401:
                    self.result.emit("Invalid API key")
                else:
                    self.result.emit(f"Connection failed (HTTP {response.status_code})")
        except Exception:
            self.result.emit("Connection failed. Check your network.")
        finally:
            self.key = ""


class CleanupJob(QThread):
    result = Signal(object)

    def __init__(self, paths, limit, startup=False, clear=False, parent=None):
        super().__init__(parent)
        self.paths, self.limit, self.startup, self.clear = paths, limit, startup, clear

    def run(self):
        try:
            usage = cleanup(self.paths, self.limit, startup=self.startup, clear_all=self.clear,
                            cancel=self.isInterruptionRequested)
            self.result.emit(usage)
        except Exception:
            logging.exception("Runtime cleanup failed")
            self.result.emit(None)


class Controller(QObject):
    def __init__(self, app, paths, startup_path, icon, background=False):
        super().__init__()
        self.app, self.paths, self.startup_path = app, paths, startup_path
        self.config = ConfigStore(paths.config)
        first_start = not self.config.path.exists()
        self.settings = self.config.load()
        self.history = HistoryStore(paths.history)
        self.main = MainWindow(paths)
        self.main.setWindowIcon(icon)
        self.main.refresh(self.settings)
        self.capture_window = self.overlay = self.result_dialog = self.settings_dialog = None
        self.history_dialog = None
        self.capture = None
        self.blocks = []
        self.result_text = ""
        self.busy = False
        self.capture_starting = False
        self.capture_hides = []
        self.ai_job = self.api_job = None
        self.cleanup_job = None
        self.cleanup_startup = True
        self.cleanup_clear_pending = False
        self.cleanup_repeat_pending = False
        self.quit_pending = False
        self.pending_task = None
        self.ai_automatic = False
        self.ai_background = False
        self.ai_capture = self.ai_overlay = None
        self.result_ai_used = False
        self.ocr = OcrService(paths)
        self.ocr.ready.connect(self._ocr_ready)
        self.ocr.completed.connect(self._recognized)
        self.ocr.failed.connect(self._ocr_error)
        self.hotkey = GlobalHotkey(app)
        self.hotkey.activated.connect(self.begin_capture)
        self.tray = QSystemTrayIcon(icon,self)
        menu = QMenu()
        for title,callback in (("Capture",self.begin_capture),("Open DeepPick AI",self.show_main),
                               ("Settings",self.open_settings),("History",self.open_history)):
            action = QAction(title,menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        credit = QAction("Developer:Chunze Liu",menu)
        credit.setEnabled(False)
        menu.addAction(credit)
        exit_action = QAction("Exit",menu)
        exit_action.triggered.connect(self.quit)
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("DeepPick AI · Developer:Chunze Liu")
        self.tray.activated.connect(lambda reason:self.show_main() if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray.show()
        self.main.capture_requested.connect(self.begin_capture)
        self.main.settings_requested.connect(self.open_settings)
        self.main.history_requested.connect(self.open_history)
        self.main.result_requested.connect(self.open_result)
        self.main.auto_enhance_changed.connect(self._set_auto_enhance)
        self.server = QLocalServer(self)
        self.server.listen("DeepPickAI-ChunzeLiu-1")
        self.server.newConnection.connect(self._new_connection)
        self.maintenance = QTimer(self)
        self.maintenance.setInterval(5*60*1000)
        self.maintenance.timeout.connect(self._maintenance)
        self.maintenance.start()
        try:
            self.hotkey.register(self.settings.capture_key)
        except (ValueError,RuntimeError) as error:
            QTimer.singleShot(500,lambda message=str(error):self.notify(message,True))
        if self.config.warning:
            QTimer.singleShot(600,lambda:self.notify(self.config.warning,True))
        if first_start or self.config.migrated:
            self.config.save(self.settings)
        link = self.startup_path / "DeepPick AI.lnk"
        if self.settings.autostart != link.exists():
            try:
                apply_autostart(self.settings.autostart, self.paths.root / "DeepPickAI.exe", self.startup_path)
            except Exception as error:
                QTimer.singleShot(700, lambda message=str(error): self.notify(message, True))
        if not background or not self.settings.start_hidden or not QSystemTrayIcon.isSystemTrayAvailable():
            self.show_main()
        QTimer.singleShot(0,self.ocr.start)
        QTimer.singleShot(750,self._maintenance)

    def _new_connection(self):
        socket = self.server.nextPendingConnection()
        if socket:
            def receive():
                command = bytes(socket.readAll())[:64]
                socket.readyRead.disconnect(receive)
                socket.disconnectFromServer()
                socket.deleteLater()
                # Finish the socket signal before closing its owning server or
                # tearing down Qt windows; otherwise PySide can use a freed slot.
                if command in (b"quit", b"show"):
                    QTimer.singleShot(0, self.quit if command == b"quit" else self.show_main)
            socket.readyRead.connect(receive)
            if socket.bytesAvailable():
                receive()

    def show_main(self):
        if self.quit_pending:
            return
        # Keep the native window out of composition until the first white frame
        # has actually painted. This also avoids a blank/black frame on cold start.
        import ctypes
        cloaked = False
        hwnd = int(self.main.winId())
        value = ctypes.c_int(1)
        if not self.main.isVisible():
            try:
                cloaked = ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd),13,ctypes.byref(value),4)==0
            except OSError:
                pass
        try:
            self.main.showNormal()
            self.main.repaint()
            if cloaked:
                ctypes.windll.dwmapi.DwmFlush()
        finally:
            if cloaked:
                value.value = 0
                ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd),13,ctypes.byref(value),4)
        self.main.raise_()
        self.main.activateWindow()

    def notify(self,message,error=False):
        self.main.set_status(message)
        if error:
            self.tray.showMessage("DeepPick AI", message, QSystemTrayIcon.MessageIcon.Warning, 4000)

    def _ocr_ready(self):
        if self.overlay and not self.overlay.ready:
            self.overlay.set_processing("Recognizing…")
        if not self.busy:
            self.main.set_status("")

    def _set_auto_enhance(self, enabled):
        settings = replace(self.settings, mode="auto", auto_enhance=enabled)
        try:
            self.config.save(settings)
        except Exception:
            self.main.refresh(self.settings)
            self.notify("Could not save settings. Check available disk space.", True)
            return
        self.settings = settings
        self.main.refresh(settings)
        if self.settings_dialog:
            self.settings_dialog.original = replace(self.settings_dialog.original, mode="auto", auto_enhance=enabled)
        if not enabled and self.ai_job and self.ai_automatic:
            self.ai_job.requestInterruption()
        if self.result_dialog:
            self.result_dialog.set_ai_enabled(self._can_ai())

    def begin_capture(self):
        if self.busy or self.quit_pending:
            self.notify("Processing…")
            return
        if self.capture_window or self.capture_starting:
            return
        self.capture_starting = True
        if self.ai_job:
            self.ai_job.requestInterruption()
        windows = [self.main, self.result_dialog, self.settings_dialog, self.history_dialog, self.overlay]
        if self.overlay:
            windows.append(self.overlay.toolbar)
        self.capture_hides, delay = hide_capture_sources(windows)
        self.close_overlay()
        if self.result_dialog:
            self.result_dialog.hide()
        if self.settings_dialog:
            self.settings_dialog.hide()
        if self.history_dialog:
            self.history_dialog.hide()
        self.main.hide()
        QTimer.singleShot(delay,self._capture)

    def _capture(self):
        self.capture_starting = False
        if self.quit_pending:
            restore_capture_sources(self.capture_hides)
            self.capture_hides = []
            return
        try:
            # Cloaking removes the hide-animation surface; the deferred frame
            # and compositor flush let newly exposed windows paint underneath.
            flush_desktop()
            self.capture_window = CaptureWindow(self.settings.cancel_key)
            restore_capture_sources(self.capture_hides)
            self.capture_hides = []
            self.capture_window.captured.connect(self._captured)
            self.capture_window.cancelled.connect(self._capture_cancelled)
            self.capture_window.open()
        except Exception as error:
            logging.exception("Screen capture failed")
            self.capture_window = None
            self.notify(str(error) or "Capture failed. Please try again.",True)
        finally:
            restore_capture_sources(self.capture_hides)
            self.capture_hides = []

    def _capture_cancelled(self):
        self.capture_window = None
        self.main.set_status("")

    def _captured(self,capture):
        self.capture_window = None
        self.capture = capture
        self.blocks = []
        self.result_text = ""
        self.result_ai_used = False
        self.busy = True
        self.main.capture_button.setEnabled(False)
        self.notify("Recognizing text…")
        self.overlay = TextOverlay(capture, None, self.settings)
        self._bind_overlay()
        if not self.ocr.available:
            self.overlay.set_processing("Preparing OCR…")
        self.overlay.open()
        QTimer.singleShot(0, lambda current=capture:self._recognize_capture(current))

    def _recognize_capture(self, capture):
        if self.quit_pending or not self.busy or self.capture is not capture or not self.overlay:
            return
        try:
            self.ocr.recognize(capture)
        except Exception as error:
            self._ocr_error(str(error))

    def _recognized(self,blocks):
        self.blocks = blocks
        self.result_text = all_text(blocks)
        self.busy = False
        self.main.capture_button.setEnabled(True)
        if self.overlay:
            self.overlay.set_blocks(blocks)
            if not blocks:
                self.overlay.state_text = 'No text found'
                self.overlay.toolbar.refresh(self.overlay)
        if blocks:
            self._present_result()
        if should_enhance(self.settings,blocks):
            self._start_ai("enhance",automatic=True)
        elif not blocks:
            self._present_result()

    def _present_result(self,save=True,source="local"):
        if not self.blocks:
            if self.result_text:
                if save:
                    self.save_history(source)
                self.open_result()
                self.main.set_status("")
                return
            self.notify("No text found. Capture another area.",True)
            return
        if save:
            self.save_history(source)
        self.main.set_status("")
        self.open_overlay()

    def save_history(self,source):
        if self.settings.history_enabled and self.result_text:
            try:
                self.history.add(self.result_text,[b.to_dict() for b in self.blocks],source)
            except OSError:
                self.notify("Recognition completed, but history could not be saved. Check disk space.",True)

    def open_overlay(self):
        if not self.blocks or not self.capture:
            return
        if self.overlay and self.overlay.capture is self.capture:
            return
        self.overlay = TextOverlay(self.capture,self.blocks,self.settings)
        if self.result_ai_used:
            self.overlay.set_blocks(self.blocks, ai_used=True)
        self._bind_overlay()
        self.overlay.open()

    def _bind_overlay(self):
        self.overlay.copied.connect(self.copy)
        self.overlay.closed.connect(self._overlay_closed)
        self.overlay.result_requested.connect(self.open_result)
        self.overlay.enhance.connect(lambda: self._start_ai("enhance"))
        self.overlay.set_ai_busy(bool(self.ai_job and self.ai_capture is self.capture))

    def _overlay_closed(self):
        pending_ocr = self.overlay and not self.overlay.ready
        self.overlay = None
        if self.busy and (pending_ocr or not self.ai_job):
            self.ocr.cancel()
            self.busy = False
            self.main.capture_button.setEnabled(True)
            self.main.set_status("")

    def close_overlay(self):
        if self.overlay:
            self.overlay.close()
            self.overlay = None

    def copy(self,text):
        self.app.clipboard().setText(text)
        self.notify("Copied")

    def _ocr_error(self,message):
        self.busy = False
        self.main.capture_button.setEnabled(True)
        if self.overlay and not self.overlay.ready:
            self.overlay.set_blocks([])
            self.overlay.state_text = "Recognition failed · Try again"
            self.overlay.toolbar.refresh(self.overlay)
        self.notify(message,True)

    def _can_ai(self):
        return bool(self.settings.api_key)

    def _start_ai(self,task,automatic=False):
        if automatic and not self.settings.auto_enhance:
            return
        if not self._can_ai():
            self.notify("Add an API key in Settings.",True)
            return
        if self.busy or self.ai_job or not self.capture:
            if not automatic and self.ai_job:
                self.notify("Enhancing with AI…")
            return
        self.ai_automatic = automatic
        self.ai_background = task == "enhance"
        self.ai_capture, self.ai_overlay = self.capture, self.overlay
        if not self.ai_background:
            self.close_overlay()
            self.busy = True
            self.main.capture_button.setEnabled(False)
        self.pending_task = task
        self.notify("Enhancing with AI…")
        self.ai_job = AiJob(task,self.capture,list(self.blocks),self.settings)
        self.ai_job.completed.connect(self._ai_completed)
        self.ai_job.failed.connect(self._ai_failed)
        self.ai_job.finished.connect(self._ai_finished)
        if self.overlay:
            self.overlay.set_ai_busy(True)
        self.ai_job.start()

    def _ai_completed(self,blocks,text):
        if not self.ai_job or self.ai_job.isInterruptionRequested() or self.ai_capture is not self.capture:
            return
        if self.pending_task == "enhance":
            self.blocks = blocks
            self.result_ai_used = True
        self.result_text = text
        self.busy = False
        self.main.capture_button.setEnabled(True)
        self.save_history("ai")
        if self.pending_task == "enhance":
            if not self.ai_overlay:
                self._present_result(save=False,source="ai")
            elif self.overlay is self.ai_overlay:
                self.overlay.set_blocks(blocks, ai_used=True, preserve_selection=True)
            self.main.set_status("")
        else:
            self.open_result()
            self.main.set_status("")
        if self.result_dialog:
            self.result_dialog.text.setPlainText(text)
            self.result_dialog.heading.setText("Recognized text · AI enhanced")

    def _ai_failed(self,message):
        if not self.ai_job or self.ai_job.isInterruptionRequested() or self.ai_capture is not self.capture:
            return
        self.busy = False
        self.main.capture_button.setEnabled(True)
        if not self.ai_background:
            self.save_history("local")
        if self.blocks and not self.overlay and not self.ai_background:
            self.open_overlay()
        if self.overlay:
            self.overlay.mark_ai_failed()
        self.notify(message,True)

    def _ai_finished(self):
        job = self.ai_job
        if self.overlay and self.ai_capture is self.capture:
            if job and job.isInterruptionRequested():
                self.overlay.mark_ai_failed(canceled=True)
            else:
                self.overlay.set_ai_busy(False)
        if job and job.isInterruptionRequested() and not self.ai_background:
            self.busy = False
            self.main.capture_button.setEnabled(True)
        if job and job.isInterruptionRequested() and not self.busy:
            self.main.set_status("")
        self.ai_job = None
        self.pending_task = None
        self.ai_capture = self.ai_overlay = None
        if job:
            job.deleteLater()
        self._finish_quit()

    def open_result(self):
        if not self.result_text and not self.blocks:
            self.notify("Capture an area first")
            return
        self.close_overlay()
        if self.result_dialog:
            self.result_dialog.close()
        self.result_dialog = ResultDialog(self.result_text,self.blocks,self._can_ai(),self.main)
        self.result_dialog.heading.setText("Recognized text · "+("AI enhanced" if self.result_ai_used else "Local OCR"))
        self._track_dialog("result_dialog",self.result_dialog)
        self.result_dialog.ai_requested.connect(self._start_ai)
        self.result_dialog.overlay_requested.connect(self._show_overlay_from_result)
        self.result_dialog.show()
        self.result_dialog.raise_()

    def _show_overlay_from_result(self):
        if self.result_dialog:
            self.result_dialog.hide()
        self.open_overlay()

    def open_settings(self):
        if self.busy:
            self.notify("Processing…")
            return
        self.close_overlay()
        if self.settings_dialog:
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            return
        self.settings_dialog = SettingsDialog(self.settings,self.startup_path,self.main)
        self._track_dialog("settings_dialog",self.settings_dialog)
        self.settings_dialog.save_requested.connect(self._save_settings)
        self.settings_dialog.test_requested.connect(self._test_api)
        self.settings_dialog.clear_cache_requested.connect(self._clear_cache)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self._maintenance()

    def _save_settings(self,settings):
        previous = self.settings
        try:
            sequences = [settings.capture_key,settings.copy_key,settings.cancel_key]
            if any(not x for x in sequences) or len(set(sequences)) != 3:
                raise ValueError("Shortcuts must be set and must be different.")
            # Validate before changing either active registration or persisted state.
            hotkey_parts(settings.capture_key)
            hotkey_parts(settings.copy_key)
            if settings.cancel_key not in ("Esc","Escape"):
                hotkey_parts(settings.cancel_key)
            if any(c.isspace() for c in settings.api_key):
                raise ValueError("The API key must not contain spaces or line breaks.")
            self.hotkey.register(settings.capture_key)
            apply_autostart(settings.autostart,self.paths.root / "DeepPickAI.exe",self.startup_path)
            self.config.save(settings)
        except Exception as error:
            try:
                self.hotkey.register(previous.capture_key)
                apply_autostart(previous.autostart,self.paths.root / "DeepPickAI.exe",self.startup_path)
            except Exception:
                logging.warning("Settings rollback could not fully restore startup/hotkey")
            self.settings_dialog.error.setText(str(error))
            return
        self.settings = settings
        self.main.refresh(settings)
        self.settings_dialog.accept()
        self.notify("Settings saved")
        self._maintenance()

    def _test_api(self,key):
        if self.api_job:
            self.settings_dialog.test_finished("Testing connection…")
            return
        self.api_job = ApiCheck(key)
        dialog = self.settings_dialog
        self.api_job.result.connect(dialog.test_finished)
        self.api_job.finished.connect(self._api_finished)
        self.api_job.start()

    def _api_finished(self):
        job = self.api_job
        self.api_job = None
        if job:
            job.deleteLater()
        self._finish_quit()

    def open_history(self):
        self.close_overlay()
        if self.history_dialog:
            self.history_dialog.refresh()
            self.history_dialog.show()
            self.history_dialog.raise_()
            return
        self.history_dialog = HistoryDialog(self.history,self.main)
        self._track_dialog("history_dialog",self.history_dialog)
        self.history_dialog.show()
        self.history_dialog.raise_()

    def _track_dialog(self,name,dialog):
        def finished(code):
            if getattr(self,name) is dialog:
                setattr(self,name,None)
            dialog.deleteLater()
        dialog.finished.connect(finished)

    def _clear_cache(self):
        self.cleanup_clear_pending = True
        if self.settings_dialog:
            self.settings_dialog.clear_cache_button.setEnabled(False)
            self.settings_dialog.storage_usage.setText("Cleaning…")
        self._maintenance()

    def _maintenance(self):
        if self.quit_pending:
            return
        if self.cleanup_job:
            self.cleanup_repeat_pending = True
            return
        self.cleanup_repeat_pending = False
        self.cleanup_job = CleanupJob(self.paths, self.settings.cache_limit_mb,
                                      startup=self.cleanup_startup, clear=self.cleanup_clear_pending,
                                      parent=self)
        self.cleanup_startup = False
        self.cleanup_clear_pending = False
        self.cleanup_job.result.connect(self._cleanup_result)
        self.cleanup_job.finished.connect(self._cleanup_finished)
        self.cleanup_job.start(QThread.Priority.LowPriority)

    def _cleanup_result(self, usage):
        if self.settings_dialog:
            self.settings_dialog.clear_cache_button.setEnabled(True)
            if usage is None:
                text = "Cleanup is unavailable. Try again."
            else:
                text = f"Cache and temporary files: {usage.runtime / 1048576:.1f} MB · Logs: {usage.logs / 1048576:.1f} MB"
                if usage.runtime > self.settings.cache_limit_mb * 1048576:
                    text += "\nSome files are in use. Cleanup will retry later."
            self.settings_dialog.storage_usage.setText(text)

    def _cleanup_finished(self):
        job = self.cleanup_job
        self.cleanup_job = None
        job.deleteLater()
        if self.cleanup_clear_pending or self.cleanup_repeat_pending:
            self._maintenance()
        self._finish_quit()

    def quit(self):
        self.quit_pending = True
        self.hotkey.close()
        self.close_overlay()
        if self.capture_window:
            self.capture_window.close()
        self.ocr.stop()
        if self.ai_job:
            self.ai_job.requestInterruption()
        if self.api_job:
            self.api_job.requestInterruption()
        self.maintenance.stop()
        if self.cleanup_job:
            self.cleanup_job.requestInterruption()
        if self.ai_job or self.api_job:
            self.notify("Exiting…")
            self.main.hide()
        self._finish_quit()

    def _finish_quit(self):
        if self.quit_pending and not self.ai_job and not self.api_job and not self.cleanup_job:
            self.tray.hide()
            self.server.close()
            self.main.exiting = True
            self.main.close()
            self.app.quit()
