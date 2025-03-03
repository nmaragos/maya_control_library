import os

import maya.cmds as mc
import maya.OpenMayaUI as omui
import pymel.core as pm
from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QMainWindow, QMenu, QVBoxLayout
from shiboken6 import wrapInstance

import control_gen_api as cgen
import constants
from logger.logger import Logger

logger = Logger()
logger.set_level("INFO")
logger.set_propagate(False)


class CustomListWidget(QListWidget):
    """A customised version of QListWidget that allows for context menus.
    It will be used to substitute the original QListWidget in the .ui file.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = QAction("Delete", self)
        menu.addAction(delete_action)

        delete_action.triggered.connect(lambda: self.delete_item())

        menu.exec_(event.globalPos())

    def delete_item(self):
        item = self.currentItem()
        if item:
            cgen.delete_controller(item.text())
            self.takeItem(self.row(item))


class ControllerLibrary(QDialog):
    def __init__(self, parent=None):
        super(ControllerLibrary, self).__init__(parent)

        loader = QUiLoader()
        current_dir = os.path.dirname(__file__)
        ui_filepath = QFile(os.path.join(current_dir, "control_gen.ui"))
        ui_filepath.open(QFile.OpenModeFlag.ReadOnly)
        self.ui = loader.load(ui_filepath, parentWidget=self)
        ui_filepath.close()

        if not self.ui:
            raise RuntimeError(loader.errorString())

        self.init_ui()
        self.set_signals()
        self.ui.show()

        if parent:
            parent_width = parent.width()
            parent_height = parent.height()

            ui_width = 250
            ui_height = 650

            pos_x = parent_width * 0.5 - ui_width * 0.5 + parent.x()
            pos_y = parent_height * 0.5 - ui_height * 0.5 + parent.y()

            self.ui.setGeometry(pos_x, pos_y, ui_width, ui_height)

    def init_ui(self):
        self.controlListWidget = CustomListWidget(self.ui.controlListWidget.parent())
        layout = self.ui.findChild(QVBoxLayout, "verticalLayout")
        layout.addWidget(self.controlListWidget)
        original_list_widget = self.ui.findChild(QListWidget, "controlListWidget")
        layout.removeWidget(original_list_widget)
        original_list_widget.deleteLater()

        self.update_control_list_widget()
        self.set_controller_colour(0)
        self.load_controller_icon()

    def set_signals(self):
        self.controlListWidget.itemDoubleClicked.connect(self.import_controller)
        self.controlListWidget.itemClicked.connect(self.replace_controller_name)
        self.controlListWidget.itemClicked.connect(self.load_controller_icon)
        self.ui.scaleSlider.valueChanged.connect(self.set_controller_scale)     #int
        self.ui.scaleValLineEdit.textChanged.connect(self.update_scale_slider)  #str
        self.ui.saveControlButton.clicked.connect(self.export_controller)
        self.ui.colourSwatchSlider.valueChanged.connect(self.set_controller_colour) #int
        self.ui.controlNameLineEdit.editingFinished.connect(self.controlListWidget.clearSelection)

    def load_controller_icon(self, icon=""):
        """Load an image relative to the conroller selected, on a QLabel.

        Args:
            icon (str, QListWidgetItem): The controller name to match to the controller icon.
        """
        icon_name = icon
        if isinstance(icon, QListWidgetItem):
            icon_name = icon.text()

        icon_filepath = os.path.join(constants.ICONS_FOLDER, f"{icon_name}.png")
        
        if not os.path.isfile(icon_filepath):
            icon_filepath = constants.NO_ICON

        pixmap = QPixmap(icon_filepath).scaled(
            self.ui.iconLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.ui.iconLabel.setPixmap(pixmap)

    def replace_controller_name(self, select_control):
        """Update the controller name on the QLineEdit box, when one is selected from the list."""
        self.ui.controlNameLineEdit.setText(select_control.text())

    def update_control_list_widget(self):
        """Refresh the contents of the controllers' list."""
        control_list = cgen.controller_list()
        self.controlListWidget.clear()
        for control_item in control_list:
            item = QListWidgetItem(control_item)
            self.controlListWidget.addItem(item)

    def import_controller(self, controller):
        """Import the selected controller into Maya.
        
        Args:
            controller (QListWidgetItem): The item selected from the list of controllers.
        """
        cgen.load_controller(
            controller.text(),
            float(self.ui.scaleValLineEdit.text()),
            colour=self.ui.colourSwatchSlider.value()
        )
    
    def export_controller(self):
        """Save selected curve to controllers library."""
        try:
            selection = pm.selected()[0]
        except:
            logger.warning("Nothing selected")
            mc.confirmDialog(title="Error", message="No curve selected!", icon="critical", button=["Cancel"])
            return

        if selection.getShape().nodeType() != "nurbsCurve":
            logger.error("Selected item should be a NURBS curve!")
            return

        curve_name = self.ui.controlNameLineEdit.text()

        if not curve_name:
            logger.error("Please enter a name for the new controller...")
            return
        
        cgen.save_controller(curve=selection, curve_name=curve_name, create_icon=True)

        self.update_control_list_widget()
        self.load_controller_icon(curve_name)

    def set_controller_scale(self, value):
        """Set a scale value for the controller to be imported.
        The amount needs to be passed as multiples of ten to accomodate for decimal values in the ui.
        
        Args:
            value (int): The scale amount.
        """
        scale_value = float(value)/10.0
        self.ui.scaleValLineEdit.setText(str(scale_value))

    def update_scale_slider(self, value):
        """Update the scale slider position, when a scale value is manually entered.
        
        Args:
            value (float): The scaling amount, manually entered.
        """
        if value:
            self.ui.scaleSlider.setValue(float(value) * 10)

    def set_controller_colour(self, colour):
        """Set the colour of the controller to be imported.
        The actual colour value corresponds to Maya's colour numbers for overrides
        and is converted to an RGB representation to be shown in the ui.
        
        Args:
            colour (int): The colour value from the relative slider.
        """
        if colour:
            rgb_colour = ",".join(
                str(color) for color in constants.maya_colour_map[colour]
            )
            self.ui.colourSwatchLabel.setStyleSheet(f"background-color:rgb({rgb_colour})")
        else:
            self.ui.colourSwatchLabel.setStyleSheet("")


def get_maya_window():
    """Pointer to the Maya main window"""
    ptr = omui.MQtUtil.mainWindow()
    if ptr:
        return wrapInstance(int(ptr), QMainWindow)


def run():
    global win
    win = ControllerLibrary(parent=get_maya_window())
