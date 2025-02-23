import os

import maya.OpenMayaUI as omui
import pymel.core as pm
from PySide6 import QtCore, QtUiTools, QtWidgets
from shiboken6 import wrapInstance

import control_gen_api as cgen
from logger.logger import Logger


logger = Logger()
logger.set_propagate(False)


class ControllerLibrary(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ControllerLibrary, self).__init__(parent)

        loader = QtUiTools.QUiLoader()
        current_dir = os.path.dirname(__file__)
        ui_filepath = QtCore.QFile(os.path.join(current_dir, "control_gen.ui"))
        ui_filepath.open(QtCore.QFile.OpenModeFlag.ReadOnly)
        self.ui = loader.load(ui_filepath, parentWidget=self)
        ui_filepath.close()

        self.init_ui()
        self.set_signals()
        self.ui.show()

        if parent:
            parent_width = parent.width()
            parent_height = parent.height()

            ui_width = 250
            ui_height = 375

            pos_x = parent_width * 0.5 - ui_width * 0.5 + parent.x()
            pos_y = parent_height * 0.5 - ui_height * 0.5 + parent.y()

            self.ui.setGeometry(pos_x, pos_y, ui_width, ui_height)

    def init_ui(self):
        self.update_control_list_widget()

    def set_signals(self):
        self.ui.controlListWidget.itemDoubleClicked.connect(self.import_controller)
        self.ui.scaleSlider.valueChanged[int].connect(self.set_controller_scale)
        self.ui.scaleValLineEdit.textChanged[str].connect(self.update_scale_slider)
        self.ui.saveControlButton.clicked.connect(self.export_controller)

    def update_control_list_widget(self):
        control_list = cgen.controller_list()
        self.ui.controlListWidget.clear()
        for control_item in control_list:
            item = QtWidgets.QListWidgetItem(control_item)
            self.ui.controlListWidget.addItem(item)

    def import_controller(self):
        """Import controller from library"""
        import_control_name = self.sender().currentItem().text()
        cgen.generate_controller(
            import_control_name,
            float(self.ui.scaleValLineEdit.text())
        )
    
    def export_controller(self):
        """Save selected curve to controllers library."""
        selection = pm.selected()[0]

        if not selection:
            logger.warning("Nothing selected")
            return

        if selection.getShape().nodeType() != "nurbsCurve":
            logger.error("Selected item should be a NURBS curve!")
            return

        curve_name = self.ui.controlNameLineEdit.text()

        if not curve_name:
            logger.error("Please enter a name for the new controller...")
            return
        
        cgen.save_controller(curve=selection, curve_name=curve_name)

        self.update_control_list_widget()

    def set_controller_scale(self, value):
        scale_value = float(value)/10.0
        self.ui.scaleValLineEdit.setText(str(scale_value))

    def update_scale_slider(self, value):
        """Update the scale slider position, when a scale value is manually entered."""
        if value:
            self.ui.scaleSlider.setValue(float(value) * 10)


def get_maya_window():
    """Pointer to the Maya main window"""
    ptr = omui.MQtUtil.mainWindow()
    if ptr:
        return wrapInstance(int(ptr), QtWidgets.QMainWindow)


def run():
    global win
    win = ControllerLibrary(parent=get_maya_window())
