import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Créer l'application Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Antigravity Manga Scraper & Downloader")
    app.setOrganizationName("Antigravity")

    # Lancer la fenêtre principale
    window = MainWindow()
    window.show()

    # Exécuter la boucle d'événements
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
