import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app_info import APP_NAME, APP_VERSION
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    smoke_test = "--smoke-test" in sys.argv
    window = MainWindow(check_updates=not smoke_test)
    window.show()
    if smoke_test:
        QTimer.singleShot(300, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
