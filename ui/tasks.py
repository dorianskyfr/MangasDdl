"""Keep background threads alive until Qt has actually finished them."""
from PySide6.QtCore import QThread, QTimer

_workers = set()
_collector = None


def active_workers():
    return [worker for worker in _workers if not worker.isFinished()]


def _collect():
    for worker in list(_workers):
        if worker.isFinished():
            _workers.discard(worker)


class ManagedThread(QThread):
    def start(self, *args, **kwargs):
        global _collector
        _workers.add(self)
        if _collector is None:
            _collector = QTimer()
            _collector.timeout.connect(_collect)
            _collector.start(250)
        super().start(*args, **kwargs)
