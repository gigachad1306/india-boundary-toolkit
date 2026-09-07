import os
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsSettings

from .provider import IndiaBoundaryToolkitProvider

SETTINGS_KEY = "india_boundary_toolkit/boundary_gpkg_path"


class IndiaBoundaryToolkitPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.load_action = None
        self.configure_action = None

    def initGui(self):
        self.provider = IndiaBoundaryToolkitProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.load_action = QAction(icon, "Load India Boundaries", self.iface.mainWindow())
        self.load_action.triggered.connect(self.load_boundaries)
        self.iface.addToolBarIcon(self.load_action)
        self.iface.addPluginToMenu("&India Boundary Toolkit", self.load_action)

        self.configure_action = QAction("Set Boundary GeoPackage Path\u2026", self.iface.mainWindow())
        self.configure_action.triggered.connect(self.configure_path)
        self.iface.addPluginToMenu("&India Boundary Toolkit", self.configure_action)

    def configure_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "Select India admin boundary GeoPackage",
            "",
            "GeoPackage (*.gpkg)",
        )
        if path:
            QgsSettings().setValue(SETTINGS_KEY, path)
            QMessageBox.information(
                self.iface.mainWindow(),
                "India Boundary Toolkit",
                "Boundary GeoPackage path saved.",
            )

    def load_boundaries(self):
        path = QgsSettings().value(SETTINGS_KEY, "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(
                self.iface.mainWindow(),
                "India Boundary Toolkit",
                "No boundary GeoPackage configured yet. Use "
                "'Set Boundary GeoPackage Path\u2026' first \u2014 point it at "
                "your maintained state/district GeoPackage (the one with "
                "the corrected state_id / Ladakh-J&K split you already "
                "maintain for India Drought Monitor).",
            )
            return

        # Load every layer in the GeoPackage (typically 'states' and 'districts')
        gpkg_layer = QgsVectorLayer(path, "boundaries", "ogr")
        sublayers = gpkg_layer.dataProvider().subLayers()
        if not sublayers:
            self.iface.addVectorLayer(path, os.path.basename(path), "ogr")
            return

        for sublayer in sublayers:
            name = sublayer.split(QgsVectorLayer.subLayerSeparator())[1]
            uri = f"{path}|layername={name}"
            layer = QgsVectorLayer(uri, name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
            else:
                self.iface.messageBar().pushWarning(
                    "India Boundary Toolkit", f"Could not load sublayer '{name}'"
                )

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removeToolBarIcon(self.load_action)
        self.iface.removePluginMenu("&India Boundary Toolkit", self.load_action)
        self.iface.removePluginMenu("&India Boundary Toolkit", self.configure_action)
