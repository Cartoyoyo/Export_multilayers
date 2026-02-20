from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os


class ExportCouchesPlugin:
    def __init__(self, iface):
        self.iface     = iface
        self.action    = None
        self.icon_path = os.path.join(
            os.path.dirname(__file__), "icon.png"
        )

    def initGui(self):
        self.action = QAction(
            QIcon(self.icon_path),
            "Export Couches Vecteur",
            self.iface.mainWindow()
        )
        self.action.setToolTip("Exporter les couches vecteur du projet")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Export Couches Vecteur", self.action)

    def unload(self):
        self.iface.removePluginMenu("&Export Couches Vecteur", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.action:
            del self.action

    def run(self):
        from .export_dialog import ExportDialog
        dialog = ExportDialog(self.iface.mainWindow())
        dialog.exec_()