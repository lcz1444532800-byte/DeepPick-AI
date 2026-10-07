from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from multiprocessing.shared_memory import SharedMemory

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal
from PySide6.QtGui import QImage

from .domain import Block, reading_order


def release_memory(memory):
    memory.close()
    memory.unlink()


class OcrService(QObject):
    ready = Signal()
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self.process = None
        self.buffer = b''
        self.pending = None
        self.retired = {}
        self.sent = set()
        self.available = False
        self.stopping = False
        self.last_timings = {}
        self.restart_count = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda:self._fail('Recognition timed out. Try a smaller capture.'))
        self.recovery = QTimer(self)
        self.recovery.setSingleShot(True)
        self.recovery.timeout.connect(self.start)

    def start(self):
        if self.process is not None: return
        self.stopping = False
        self.buffer = b''
        process = self.process = QProcess(self)
        process.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        process.setWorkingDirectory(str(self.paths.root))
        process.readyReadStandardOutput.connect(self._read)
        process.readyReadStandardError.connect(lambda:logging.warning('OCR diagnostic output (%d bytes)',len(process.readAllStandardError())))
        process.errorOccurred.connect(self._process_error)
        process.finished.connect(self._finished)
        if getattr(sys, '_deeppick_runtime', False):
            process.start(sys.executable, ['-B', '-m', 'deeppick_entry', '--ocr-worker'])
        elif getattr(sys,'frozen',False):
            process.start(sys.executable,['--ocr-worker'])
        else:
            entry = os.path.join(os.path.dirname(os.path.dirname(__file__)),'main.py')
            executable = os.path.join(os.path.dirname(sys.executable),'pythonw.exe')
            process.start(executable if os.path.exists(executable) else sys.executable,['-B',entry,'--ocr-worker'])
        self.timer.start(90000)

    def recognize(self, capture):
        if self.pending: raise RuntimeError('A recognition task is already running.')
        started = time.perf_counter()
        image = capture.image.convertToFormat(QImage.Format.Format_RGB888)
        request_id = uuid.uuid4().hex
        size = image.bytesPerLine()*image.height()
        memory = SharedMemory(name='DeepPickAI_'+request_id,create=True,size=size)
        try:
            memory.buf[:size] = image.constBits()
            request = {'id':request_id,'shared_memory':memory.name,'width':image.width(),
                       'height':image.height(),'stride':image.bytesPerLine()}
            self.pending = (request,memory,capture,started)
            self.start()
            self.timer.start(90000)
            if self.available: self._send()
        except Exception:
            self.pending = None
            release_memory(memory)
            raise

    def _send(self):
        if self.pending:
            self.process.write((json.dumps(self.pending[0])+'\n').encode('utf-8'))
            self.sent.add(self.pending[0]['id'])

    def cancel(self):
        if self.pending:
            request,memory,_,_ = self.pending
            if request['id'] in self.sent:
                self.retired[request['id']] = memory
            else:
                release_memory(memory)
            self.pending = None
        self.timer.stop()

    def _read(self):
        if self.process is None: return
        self.buffer += bytes(self.process.readAllStandardOutput())
        if len(self.buffer)>8*1024*1024:
            self._fail('The OCR response is too large. Capture a smaller area.')
            return
        while b'\n' in self.buffer:
            line,self.buffer = self.buffer.split(b'\n',1)
            try:
                data = json.loads(line)
                self.sent.discard(data.get('id'))
                retired = self.retired.pop(data.get('id'),None)
                if retired is not None:
                    release_memory(retired)
                    continue
                if data.get('error'):
                    self._fail(data['error'])
                    return
                if data.get('ready'):
                    self.available = True
                    self.restart_count = 0
                    self.ready.emit()
                    if self.pending: self._send()
                    else: self.timer.stop()
                elif self.pending and data.get('id') == self.pending[0]['id']:
                    _,memory,capture,started = self.pending
                    blocks = [Block.from_dict(value,capture.image.width(),capture.image.height()) for value in data['blocks']]
                    if sum(len(block.text) for block in blocks)>60000: raise ValueError('too many characters')
                    release_memory(memory)
                    self.pending = None
                    self.timer.stop()
                    self.last_timings = {'total_seconds':time.perf_counter()-started,**data.get('timings',{})}
                    logging.info('OCR complete: %.3fs, %d regions',self.last_timings['total_seconds'],len(blocks))
                    self.completed.emit(reading_order(blocks))
            except Exception:
                logging.exception('OCR protocol rejected')
                self._fail('Invalid OCR response. Please try again.')
                return

    def _process_error(self, error):
        if not self.stopping: self._fail('Could not start OCR. Check the app folder.')

    def _finished(self, code, status):
        process = self.process
        self.process = None
        self.available = False
        if process: process.deleteLater()
        if not self.stopping: self._fail('OCR restarted. Capture again.')

    def _fail(self, message):
        self.stop()
        self.failed.emit(message)
        self.restart_count += 1
        if self.restart_count <= 3:
            self.recovery.start((250,1000,3000)[self.restart_count-1])

    def stop(self):
        self.stopping = True
        self.timer.stop()
        self.recovery.stop()
        if self.process:
            process,self.process = self.process,None
            process.blockSignals(True)
            process.kill()
            process.waitForFinished(3000)
            process.deleteLater()
        if self.pending:
            release_memory(self.pending[1])
            self.pending = None
        for memory in self.retired.values(): release_memory(memory)
        self.retired.clear()
        self.sent.clear()
        self.available = False
