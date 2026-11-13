try:
    from qgis.PyQt.QtGui import QAction        # Qt6 / QGIS 4
except ImportError:
    from qgis.PyQt.QtWidgets import QAction    # Qt5 / QGIS 3
from qgis.PyQt.QtGui import QIcon
import os


class ExportCouchesPlugin:
    """Main plugin class registered by QGIS via classFactory."""

    def __init__(self, iface):
        # Store reference to the QGIS interface
        self.iface     = iface
        self.action    = None
        self.dialog    = None
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
        if self.dialog is not None:
            try:
                self.dialog.close()
            except RuntimeError:
                pass
            self.dialog = None
        self.iface.removePluginVectorMenu("&Export Couches Vecteur", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.action:
            del self.action

    def run(self):
        """Open the export dialog (non-modal: the map stays usable to draw
        or select the export area)."""
        if self.dialog is not None:
            try:
                if self.dialog.isVisible():
                    self.dialog.raise_()
                    self.dialog.activateWindow()
                    return
                if not getattr(self.dialog, '_closed', True):   # hidden while drawing/selecting
                    self.dialog.bring_back()
                    return
                self.dialog.close()
                self.dialog.deleteLater()
            except RuntimeError:
                pass
        from .export_dialog import ExportDialog
        self.dialog = ExportDialog(self.iface.mainWindow())
        self.dialog.setModal(False)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
