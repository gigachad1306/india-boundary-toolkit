from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsCoordinateTransform,
    QgsProject,
    QgsFeature,
    QgsWkbTypes,
)


class ReprojectFixCrsAlgorithm(QgsProcessingAlgorithm):
    """
    Reprojects a layer to a target CRS, but lets you OVERRIDE the source
    CRS first. Useful for files (e.g. some govt-distributed district
    GeoJSON/shapefiles) whose declared/embedded CRS is missing or wrong
    -- for instance data that is actually Lambert Conformal Conic but
    carries no .prj / an incorrect EPSG tag, so QGIS's own reprojection
    silently produces garbage coordinates unless you tell it the true
    source CRS first.
    """

    INPUT = "INPUT"
    SOURCE_CRS_OVERRIDE = "SOURCE_CRS_OVERRIDE"
    TARGET_CRS = "TARGET_CRS"
    OUTPUT = "OUTPUT"

    def name(self):
        return "reproject_fix_source_crs"

    def displayName(self):
        return "Reproject / Fix Source CRS"

    def group(self):
        return "India Boundary Toolkit"

    def groupId(self):
        return "india_boundary_toolkit"

    def shortHelpString(self):
        return (
            "Reprojects a vector layer to a target CRS. If 'Source CRS "
            "override' is set, that CRS is used as the TRUE source CRS "
            "instead of whatever QGIS auto-detected -- use this when a "
            "file's declared CRS is missing or wrong (a common issue with "
            "Lambert Conformal Conic-projected district/state boundary "
            "files that lack a reliable .prj)."
        )

    def createInstance(self):
        return ReprojectFixCrsAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(self.INPUT, "Input layer")
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.SOURCE_CRS_OVERRIDE,
                "Source CRS override (leave blank to trust the layer's own CRS)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.TARGET_CRS,
                "Target CRS",
                defaultValue="EPSG:4326",
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Reprojected output")
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        target_crs = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
        source_override = self.parameterAsCrs(
            parameters, self.SOURCE_CRS_OVERRIDE, context
        )

        source_crs = source_override if source_override.isValid() else layer.crs()
        if source_override.isValid():
            feedback.pushInfo(
                f"Overriding source CRS: treating features as "
                f"{source_crs.authid() or source_crs.description()}"
            )

        transform = QgsCoordinateTransform(
            source_crs, target_crs, QgsProject.instance()
        )

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            layer.fields(),
            layer.wkbType(),
            target_crs,
        )

        total = layer.featureCount()
        for i, feat in enumerate(layer.getFeatures()):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            geom.transform(transform)
            out_feat = QgsFeature(feat)
            out_feat.setGeometry(geom)
            sink.addFeature(out_feat)
            if total:
                feedback.setProgress(int(100 * (i + 1) / total))

        return {self.OUTPUT: dest_id}
