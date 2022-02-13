import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QPushButton, QWidget, QSizeGrip
from PyQt6 import QtCore, QtGui
import pyscreeze  # screenshot
import pytesseract  # python tesseract 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

form_class = uic.loadUiType(BASE_DIR + r'\mainWindow.ui')[0]

# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

class SubWindow(QDialog):
    dirty = True
    regionChanged = QtCore.pyqtSignal()

    def __init__(self):
        # super().__init__()
        QDialog.__init__(self)
        print('SubWindow`s device pixel ratio', self.devicePixelRatio())
        uic.loadUi(BASE_DIR + r'\subWindow.ui', self)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.FramelessWindowHint)

        self.gripSize = 16
        self.grips = []
        for i in range(4):
            grip = QSizeGrip(self)
            grip.resize(self.gripSize, self.gripSize)
            self.grips.append(grip)

    def updateMask(self):
        frameRect = self.frameGeometry()
        
        grabGeometry = self.grabWidget.geometry()

        # geometry가 dialog부터가 아니라 자기바로위의 위젯기준으로 나온다
        grabGeometry.moveTopLeft(
            self.grabWidget.mapTo(self, QtCore.QPoint(0,0)))
        
        frameRect.moveTopLeft(QtCore.QPoint(0,0))

        region = QtGui.QRegion(frameRect)
        region -= QtGui.QRegion(grabGeometry)

        self.setMask(region)

    def resizeEvent(self, event):
        super(SubWindow, self).resizeEvent(event)
        rect = self.rect()
        # top left grip doesn't need to be moved...
        # top right
        self.grips[1].move(rect.right() - self.gripSize, 0)
        # bottom right
        self.grips[2].move(
            rect.right() - self.gripSize, rect.bottom() - self.gripSize)
        # bottom left
        self.grips[3].move(0, rect.bottom() - self.gripSize)
        # the first resizeEvent is called *before* any first-time showEvent and
        # paintEvent, there's no need to update the mask until then; see below
        if not self.dirty:
            self.updateMask()

        self.regionChanged.emit()

    def getRegion(self):
        grabWidget: QWidget = self.grabWidget
        grabGeometry = grabWidget.geometry()
        grabGeometry.moveTopLeft(
            self.grabWidget.mapToGlobal(QtCore.QPoint(0, 0)))
        return grabGeometry

    def paintEvent(self, event):
        super(SubWindow, self).paintEvent(event)
        # on Linux the frameGeometry is actually updated "sometime" after show()
        # is called; on Windows and MacOS it *should* happen as soon as the first
        # non-spontaneous showEvent is called (programmatically called: showEvent
        # is also called whenever a window is restored after it has been
        # minimized); we can assume that all that has already happened as soon as
        # the first paintEvent is called; before then the window is flagged as
        # "dirty", meaning that there's no need to update its mask yet.
        # Once paintEvent has been called the first time, the geometries should
        # have been already updated, we can mark the geometries "clean" and then
        # actually apply the mask.
        if self.dirty:
            self.updateMask()
            self.dirty = False

    def moveEvent(self, event):
        super(SubWindow, self).moveEvent(event)
        self.regionChanged.emit()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = QtCore.QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()


class MyApp(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.show()

        self.win = SubWindow()
        self.win.setModal(False)

        self.OpenSubWindow.stateChanged.connect(self.showDialog)

        # .ui 파일에있는 컴포넌트들은 타입을 유추를 못하는듯..
        pushButton2: QPushButton = self.pushButton_2
        pushButton2.clicked.connect(self.Once)

        self.win.closeEvent = self.closeDialog
        self.win.regionChanged.connect(self.updateRegion)

    def closeEvent(self, event):
        self.win.close()

    def showDialog(self, state):
        if state > 1:
            self.win.show()
        else:
            self.win.close()

    def closeDialog(self, event):
        self.OpenSubWindow.setChecked(False)

    def Once(self):
        if self.win.isVisible():
            r = self.win.getRegion()
            print(r.left(), r.top(), r.width(), r.height())

            # mac의 경우 high dpi라서 geometry()로 얻은 좌표계와 physical pixel 사이에 맞지않음.
            # 그래서 devicePixelRatio()로 스케일링 해주는 과정 필요하다
            transform = QtGui.QTransform()
            transform.scale(self.devicePixelRatio(), self.devicePixelRatio())

            r = transform.mapRect(r)
            print(r.left(), r.top(), r.width(), r.height())

            pyscreeze.screenshot(
                './screenshot.png', region=(r.left(), r.top(), r.width(), r.height()))

            # img = pyscreeze.screenshot(region=(r.left(), r.top(), r.width(), r.height()))

            # # ocr processing
            # custom_config = r'--oem 3 --psm 4'
            # ret = pytesseract.image_to_string(
            #     img, lang='eng+kor', config=custom_config)

            # print('ret', ret)
            # self.plainTextEdit.setPlainText(ret)
        else:
            print('subClass is closed')

    def updateRegion(self):
        r = self.win.getRegion()
        self.widthLabel.setText(str(r.width()))
        self.heightLabel.setText(str(r.height()))

        # 만약 'moduleA.py'라는 코드를 import해서 예제 코드를 수행하면
        #  __name__ 은 'moduleA'가 됩니다. 그렇지 않고 코드를 직접 실행한다면
        #  __name__ 은 __main__ 이 됩니다.
        # 따라서 이 한 줄의 코드를 통해 프로그램이 직접 실행되는지
        # 혹은 모듈을 통해 실행되는지를 확인합니다.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # app.setAttribute(QtCore.Qt.ApplicationAttribute.AA_Use96Dpi)
    # QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy()

    
    screens = QtGui.QGuiApplication.screens()
    i =0
    for screen in screens:
        print(i, 'screen geometry', screen.geometry(), screen.devicePixelRatio())

    ex = MyApp()
    sys.exit(app.exec())
