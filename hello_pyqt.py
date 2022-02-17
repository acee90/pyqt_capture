import sys
import os
import typing
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, \
                            QWidget, QSizeGrip, QMessageBox, QCheckBox
from PyQt6 import QtCore, QtGui
import pyscreeze  # screenshot
import pytesseract
from googletrans import Translator
from qt_material import apply_stylesheet
import requests 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

class SecondWindow(QDialog):
    selectRect = QtCore.QRect()
    def __init__(self, parent: typing.Optional[QWidget] = ...) -> None:
        super().__init__(parent)

        self.setStyleSheet("background-color: black")
        self.setWindowOpacity(0.7)
        self.setWindowState(QtCore.Qt.WindowState.WindowFullScreen)
        self.setWindowFlags(QtCore.Qt.WindowType.Window | 
                            QtCore.Qt.WindowType.FramelessWindowHint |
                            QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setMouseTracking(False)

        # shortcut 등록
        self.cancel = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Escape), self)
        self.cancel.activated.connect(self.Cancel)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.selectRect = QtCore.QRect()
        self.startPos = QtCore.QPoint()
        self.endPos = QtCore.QPoint()
        self.updateMask()
        return super().showEvent(a0)

    def Cancel(self):
        self.hide()
        self.parent().show()
    
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        self.startPos = event.pos()
        self.endPos = self.startPos
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self.endPos = event.pos()
        self.updateMask()
        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        # globalPosition으로 매핑 (할필요가 없다? frameless + fullscreen 이라서?)
        # self.selectedRegion = QtGui.QRegion(self.selectRect)

        # accept면 close, reject이면 hide 로 구분한다?
        self.close()
        self.parent().show()

    def updateMask(self):
        #뒤에 비쳐 보이도록
        frameRect = self.frameGeometry()
        frameRect.moveTopLeft(QtCore.QPoint(0,0))

        x = min(self.startPos.x(), self.endPos.x())
        y = min(self.startPos.y(), self.endPos.y())
        w = abs(self.startPos.x() - self.endPos.x())
        h = abs(self.startPos.y() - self.endPos.y())

        self.selectRect = QtCore.QRect(x, y, w, h)

        region = QtGui.QRegion(frameRect)
        region -= QtGui.QRegion(x, y, w, h)

        self.setMask(region)

    # 이건 flicker 생겨서 좀 해결하고 주석풀어야 할 듯..
    # def paintEvent(self, event: QtGui.QPaintEvent) -> None:
    #     qp = QtGui.QPainter()
    #     qp.begin(self)
        
    #     #draw white rect
    #     qpen = QtGui.QPen(QtCore.Qt.GlobalColor.white, 2, QtCore.Qt.PenStyle.SolidLine)
    #     qp.setPen(qpen)
    #     qp.drawRect(self.selectRect)

    #     qp.end()
    #     return super().paintEvent(event)

class SubWindow(QDialog):
    dirty = True
    regionChanged = QtCore.pyqtSignal()

    def __init__(self, selectedRect: QtCore.QRect):
        # super().__init__()
        QDialog.__init__(self)
        uic.loadUi(os.path.join(BASE_DIR,'subWindow.ui'), self)

        self.selectedRect = selectedRect

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.WindowType.SubWindow | QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.FramelessWindowHint)

        self.gripSize = 16
        self.grips = []
        for i in range(4):
            grip = QSizeGrip(self)
            grip.resize(self.gripSize, self.gripSize)
            self.grips.append(grip)
    
    def showByGeometry(self, r: QtCore.QRect):
        self.show()

        # calc margin
        frameRect = self.frameGeometry()
        frameRect.moveTopLeft(QtCore.QPoint(0,0))

        grabWidgetRect: QtCore.QRect = self.grabWidget.geometry()

        tl = grabWidgetRect.topLeft()

        br = frameRect.bottomRight() - grabWidgetRect.bottomRight()

        r.adjust(-tl.x(), -tl.y(), br.x(), br.y())

        self.setGeometry(r)
        # self.updateMask()

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

    # def mousePressEvent(self, event):
    #     self.oldPos = event.globalPosition().toPoint()

    # def mouseMoveEvent(self, event):
    #     delta = QtCore.QPoint(event.globalPosition().toPoint() - self.oldPos)
    #     self.move(self.x() + delta.x(), self.y() + delta.y())
    #     self.oldPos = event.globalPosition().toPoint()


class MyApp(QMainWindow):
    selectedRect = QtCore.QRect()
    def __init__(self):
        super().__init__()
        QMainWindow.__init__(self)
        uic.loadUi(os.path.join(BASE_DIR,'firstWindow.ui'), self)
        
        # self.setupUi(self)
        self.setStatusBarBySize(0, 0)
        self.show()

        # connect event
        self.startButton.clicked.connect(self.determineRegion)
        self.pictureButton.clicked.connect(self.takePicture)

        self.selector = SecondWindow(self)
        self.selector.closeEvent = self.closeSelector

        self.thirdWin = SubWindow(self)
        self.thirdWin.setModal(False)
        self.thirdWin.regionChanged.connect(lambda: self.updateRegion(self.thirdWin.getRegion()))

        self.cancel = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Escape), self)
        self.cancel.activated.connect(self.Cancel)

    def Cancel(self):
        self.selector.close()
        self.thirdWin.close()

    def determineRegion(self):
        self.thirdWin.close()
        self.selector.show()

        self.hide()

    def updateRegion(self, r: QtCore.QRect):
        self.selectedRect = r
        self.setStatusBarBySize(self.selectedRect.width(), self.selectedRect.height())

    def setStatusBarBySize(self, width: int, height: int):
        self.statusBar().showMessage(f'{width:>4d} x {height:>4d}')

    def closeSelector(self, event):
        self.updateRegion(self.selector.selectRect)
        self.setStatusBarBySize(self.selector.selectRect.width(), self.selector.selectRect.height())
        
        self.thirdWin.showByGeometry(self.selector.selectRect)
        # self.statusBar().showMessage(f'{self.selector.selectRect.width():4f} x {self.selector.selectRect.height():4f}')
        # TODO: show ThirdWindow 

    def closeDialog(self, event):
        self.OpenSubWindow.setChecked(False)

    def translate(self, ocr_string):
        # papapgo 
        detect_url = "https://openapi.naver.com/v1/papago/detectLangs"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Naver-Client-Id": "vNvZNTNJnKEeD1qh8gZO",
            "X-Naver-Client-Secret": "9y0hpEuZDx"
        }

        response = requests.post(detect_url, headers=headers, params={"query": ocr_string})
        response.raise_for_status()
        source_lang = response.json()['langCode']
        # TODO: change combobox item to source_lang

        translate_url = "https://openapi.naver.com/v1/papago/n2mt"
        data={"source": source_lang, "target": "ko", "text": ocr_string}
        response = requests.post(translate_url, headers=headers, data=data)

        if response.status_code == 200:
            print (response.json())
            if self.checkBox_appendMode.checkState() != QtCore.Qt.CheckState.Checked:
                self.texteEdit_translate.setPlainText(response.json()['message']['result']['translatedText'])
            else:
                self.texteEdit_translate.appendPlainText(response.json()['message']['result']['translatedText'])
        else:
            QMessageBox.about(self, 'Error', response.json())

    def takePicture(self):
        if self.thirdWin.isVisible():
            r = self.thirdWin.getRegion()

            # mac의 경우 high dpi라서 geometry()로 얻은 좌표계와 physical pixel 사이에 맞지않음.
            # 그래서 devicePixelRatio()로 스케일링 해주는 과정 필요하다
            transform = QtGui.QTransform()
            transform.scale(self.devicePixelRatio(), self.devicePixelRatio())

            r = transform.mapRect(r)

            # pyscreeze.screenshot(
            #     './screenshot.png', region=(r.left(), r.top(), r.width(), r.height()))

            img = pyscreeze.screenshot(region=(r.left(), r.top(), r.width(), r.height()))

            # # ocr processing
            custom_config = r'--oem 3 --psm 4'
            ret = pytesseract.image_to_string(
                img, lang='eng+kor', config=custom_config)

            self.textEdit_ocr.setPlainText(ret)
            self.translate(ret)
        else:
            print('subClass is closed')

        # 만약 'moduleA.py'라는 코드를 import해서 예제 코드를 수행하면
        #  __name__ 은 'moduleA'가 됩니다. 그렇지 않고 코드를 직접 실행한다면
        #  __name__ 은 __main__ 이 됩니다.
        # 따라서 이 한 줄의 코드를 통해 프로그램이 직접 실행되는지
        # 혹은 모듈을 통해 실행되는지를 확인합니다.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # app.setAttribute(QtCore.Qt.ApplicationAttribute.AA_Use96Dpi)
    # QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy()

    apply_stylesheet(app, theme='dark_blue.xml')
    
    screens = QtGui.QGuiApplication.screens()
    i =0
    for screen in screens:
        print(i, 'screen geometry', screen.geometry(), screen.devicePixelRatio())

    ex = MyApp()
    sys.exit(app.exec())
