from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys

class ExerciseSelector(QWidget):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("Egzersiz Seçimi")
        self.setGeometry(300, 200, 400, 200)
        self.setStyleSheet("background-color: #f5f5f5;")

        self.choice = None
        layout = QVBoxLayout()

        title = QLabel("🏋️ Akıllı Egzersiz Takip Sistemi")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dropdown = QComboBox()
        self.dropdown.addItems(config.keys())
        self.dropdown.setStyleSheet("font-size: 14px; padding: 6px;")

        self.button = QPushButton("Başla")
        self.button.setStyleSheet("font-size: 16px; padding: 8px; background-color: #4CAF50; color: white;")
        self.button.clicked.connect(self.select)

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(self.dropdown)
        layout.addSpacing(10)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def select(self):
        self.choice = self.dropdown.currentText()
        self.close()

def choose_exercise(config):
    app = QApplication(sys.argv)
    window = ExerciseSelector(config)
    window.show()
    app.exec()
    return window.choice
