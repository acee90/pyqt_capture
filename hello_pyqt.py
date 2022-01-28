import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from PyQt5 import QtCore, QtGui

form_class = uic.loadUiType("./mainWindow.ui")[0]

sub_class = uic.loadUiType("./subWindow.ui")[0]


class SubWindow(QDialog, sub_class):
    dirty = True

    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def updateMask(self):
        # get the *whole* window geometry, including its titlebar and borders
        frameRect = self.frameGeometry()

        # get the grabWidget geometry and remap it to global coordinates
        grabGeometry = self.grabWidget.geometry()
        grabGeometry.moveTopLeft(
            self.grabWidget.mapToGlobal(QtCore.QPoint(0, 0)))

        # get the actual margins between the grabWidget and the window margins
        left = frameRect.left() - grabGeometry.left()
        top = frameRect.top() - grabGeometry.top()
        right = frameRect.right() - grabGeometry.right()
        bottom = frameRect.bottom() - grabGeometry.bottom()

        # reset the geometries to get "0-point" rectangles for the mask
        frameRect.moveTopLeft(QtCore.QPoint(0, 0))
        grabGeometry.moveTopLeft(QtCore.QPoint(0, 0))

        # create the base mask region, adjusted to the margins between the
        # grabWidget and the window as computed above
        region = QtGui.QRegion(frameRect.adjusted(left, top, right, bottom))
        # "subtract" the grabWidget rectangle to get a mask that only contains
        # the window titlebar, margins and panel
        region -= QtGui.QRegion(grabGeometry)
        self.setMask(region)

        # update the grab size according to grabWidget geometry
        # self.widthLabel.setText(str(self.grabWidget.width()))
        # self.heightLabel.setText(str(self.grabWidget.height()))

    def resizeEvent(self, event):
        super(SubWindow, self).resizeEvent(event)
        # the first resizeEvent is called *before* any first-time showEvent and
        # paintEvent, there's no need to update the mask until then; see below
        if not self.dirty:
            self.updateMask()

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


class MyApp(QMainWindow, form_class):

    def __init__(self):
        super().__init__()
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.show()

        self.win = SubWindow()
        self.win.setModal(False)

        self.OpenSubWindow.stateChanged.connect(self.showDialog)

        self.win.closeEvent = self.closeDialog

    def showDialog(self, state):
        if state > 1:
            self.win.show()
        else:
            self.win.close()

    def closeDialog(self, event):
        self.OpenSubWindow.setChecked(False)

        # 만약 'moduleA.py'라는 코드를 import해서 예제 코드를 수행하면
        #  __name__ 은 'moduleA'가 됩니다. 그렇지 않고 코드를 직접 실행한다면
        #  __name__ 은 __main__ 이 됩니다.
        # 따라서 이 한 줄의 코드를 통해 프로그램이 직접 실행되는지
        # 혹은 모듈을 통해 실행되는지를 확인합니다.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
