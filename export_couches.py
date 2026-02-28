from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os


class ExportCouchesPlugin:
    """Main plugin class registered by QGIS via classFactory."""

    def __init__(self, iface):
        # Store reference to the QGIS interface
        self.iface     = iface
        self.action    = None
        self.icon_path = os.path.join(
            os.path.dirname(__file__), "icon.png"
        )

    def initGui(self):
        """Create the menu entry and toolbar icon."""
        self.action = QAction(
            QIcon(self.icon_path),
            "Export Couches Vecteur",
            self.iface.mainWindow()
        )
        self.action.setToolTip("Exporter les couches vecteur du projet")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        # Add plugin to the Vector menu
        self.iface.addPluginToVectorMenu("&Export Couches Vecteur", self.action)

    def unload(self):
        """Remove the plugin menu entry and toolbar icon."""
        self.iface.removePluginVectorMenu("&Export Couches Vecteur", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.action:
            del self.action

    def run(self):
        """Open the export dialog."""
        from .export_dialog import ExportDialog
        dialog = ExportDialog(self.iface.mainWindow())
        dialog.exec_()
