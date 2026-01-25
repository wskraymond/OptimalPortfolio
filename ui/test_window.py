import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("PyQt5 Test Window")
window.setGeometry(300, 300, 300, 150)

layout = QVBoxLayout()
label = QLabel("Hello from PyQt5!")
layout.addWidget(label)

window.setLayout(layout)
window.show()

sys.exit(app.exec_())
