import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QPushButton, QWidget, QPlainTextEdit
from PyQt6 import QtCore, QtGui

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MyApp(QMainWindow):
    def __init__(self):
        # super().__init__()
        QMainWindow.__init__(self)
        uic.loadUi(BASE_DIR + r'\mainwindow2.ui', self)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)

        self.show()
    
    def updateMask(self):
        frameRect = self.frameGeometry()

        outerRect = self.widget.geometry()
        innerRect = self.widget_3.geometry()
        # innerRect.moveTopLeft(
        #     self.widget_3.mapToGlobal(QtCore.QPoint(0, 0)))
        # # innerRegion.moveTopLeft(QtCore.QPoint(0,0))
        print(frameRect, outerRect, innerRect)

        frameRect.moveTopLeft(QtCore.QPoint(0,0))

        region = QtGui.QRegion(frameRect)
        region -= QtGui.QRegion(innerRect)

        self.setMask(region)    

    def paintEvent(self, event):
        super(QMainWindow, self).paintEvent(event)
        self.updateMask()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec())