import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms.reproject_fix_crs import ReprojectFixCrsAlgorithm
from .algorithms.assign_admin_ids import AssignAdminIdsAlgorithm


class IndiaBoundaryToolkitProvider(QgsProcessingProvider):
    def id(self):
        return "india_boundary_toolkit"

    def name(self):
        return "India Boundary Toolkit"

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        return QIcon(icon_path) if os.path.exists(icon_path) else super().icon()

    def loadAlgorithms(self):
        self.addAlgorithm(ReprojectFixCrsAlgorithm())
        self.addAlgorithm(AssignAdminIdsAlgorithm())
