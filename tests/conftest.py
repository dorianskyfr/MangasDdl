import os
import tempfile
from pathlib import Path
import pytest

_test_data = tempfile.TemporaryDirectory(prefix='mangasddl-tests-')
os.environ['MANGASDDL_DATA_DIR'] = _test_data.name
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='session')
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    from ui.tasks import active_workers
    for worker in active_workers():
        worker.requestInterruption()
        worker.wait(5000)
    app.processEvents()
