import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.widgets.splash_screen import SplashScreen

def main():
    # Créer l'application Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Antigravity Manga Scraper & Downloader")
    app.setOrganizationName("Antigravity")

    # Lancer le splash screen
    splash = SplashScreen()
    splash.show()
    splash.start()

    # Préparer la fenêtre principale
    window = MainWindow()

    def on_splash_finished():
        window.show()
        splash.close()

    splash.finished.connect(on_splash_finished)

    # Exécuter la boucle d'événements
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
