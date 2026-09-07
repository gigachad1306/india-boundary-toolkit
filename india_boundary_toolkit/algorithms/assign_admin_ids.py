from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterDistance,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsSpatialIndex,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsFeatureRequest,
    QgsGeometry,
)


def _parse_overrides(text):
    """
    Parse an override rule string of the form:
      match_field=match_value->target_field=target_value; ...
    e.g. "district_name=Ladakh->state_id=38;district_name=Jammu and Kashmir->state_id=15"
    Returns a list of (match_field, match_value, target_field, target_value) tuples.
    """
    rules = []
    text = (text or "").strip()
    if not text:
        return rules
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk or "->" not in chunk:
            continue
        match_part, target_part = chunk.split("->", 1)
        if "=" not in match_part or "=" not in target_part:
            continue
        match_field, match_value = match_part.split("=", 1)
        target_field, target_value = target_part.split("=", 1)
        rules.append((match_field.strip(), match_value.strip(),
                       target_field.strip(), target_value.strip()))
    return rules


class AssignAdminIdsAlgorithm(QgsProcessingAlgorithm):
    """
    Joins admin ID fields (state_id, district name, etc.) from a reference
    boundary layer onto an input layer of points or small polygons.
    Tries a strict spatial containment/intersection match first; for
    features that don't land cleanly inside any reference polygon (slivers,
    coastal/border grid points, tiny districts a coarse point misses) it
    falls back to nearest-boundary-by-distance, within a configurable
    search radius -- the QGIS-native equivalent of a cKDTree
    nearest-neighbour fallback. A small override table lets you force
    specific ID values for known special cases (e.g. Ladakh / J&K splits).
    """

    INPUT = "INPUT"
    REFERENCE = "REFERENCE"
    REFERENCE_ID_FIELDS = "REFERENCE_ID_FIELDS"
    MAX_DISTANCE = "MAX_DISTANCE"
    OVERRIDES = "OVERRIDES"
    OUTPUT = "OUTPUT"

    def name(self):
        return "assign_admin_ids"

    def displayName(self):
        return "Assign Admin IDs by Boundary"

    def group(self):
        return "India Boundary Toolkit"

    def groupId(self):
        return "india_boundary_toolkit"

    def shortHelpString(self):
        return (
            "Transfers ID/name fields from a reference admin-boundary layer "
            "onto an input layer, using containment first and a "
            "nearest-neighbour fallback (within Max search distance) for "
            "features that don't fall cleanly inside any boundary. Use "
            "'ID overrides' for known special cases, e.g.:\n"
            "district_name=Ladakh->state_id=38;district_name=Jammu and Kashmir->state_id=15"
        )

    def createInstance(self):
        return AssignAdminIdsAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input layer (points or small polygons)"))
        self.addParameter(QgsProcessingParameterVectorLayer(self.REFERENCE, "Reference boundary layer"))
        self.addParameter(
            QgsProcessingParameterField(
                self.REFERENCE_ID_FIELDS,
                "Fields to transfer from reference layer",
                parentLayerParameterName=self.REFERENCE,
                allowMultiple=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDistance(
                self.MAX_DISTANCE,
                "Max search distance for fallback match (layer units)",
                parentParameterName=self.INPUT,
                defaultValue=5000,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OVERRIDES,
                "ID overrides (match_field=value->target_field=value; ...)",
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, "Output layer"))

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        ref_layer = self.parameterAsVectorLayer(parameters, self.REFERENCE, context)
        id_fields = self.parameterAsFields(parameters, self.REFERENCE_ID_FIELDS, context)
        max_distance = self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
        overrides = _parse_overrides(self.parameterAsString(parameters, self.OVERRIDES, context))

        ref_features = {f.id(): f for f in ref_layer.getFeatures()}
        index = QgsSpatialIndex(ref_layer.getFeatures())

        out_fields = QgsFields(input_layer.fields())
        for fname in id_fields:
            if out_fields.indexFromName(fname) == -1:
                out_fields.append(QgsField(fname, ref_layer.fields().field(fname).type()))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, out_fields,
            input_layer.wkbType(), input_layer.crs(),
        )

        total = input_layer.featureCount()
        n_strict, n_fallback, n_unmatched = 0, 0, 0

        for i, feat in enumerate(input_layer.getFeatures()):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            matched_ref = None

            # 1. Strict containment/intersection via candidate bbox lookup
            candidate_ids = index.intersects(geom.boundingBox())
            for fid in candidate_ids:
                ref_geom = ref_features[fid].geometry()
                if ref_geom.intersects(geom):
                    matched_ref = ref_features[fid]
                    n_strict += 1
                    break

            # 2. Nearest-neighbour fallback within max_distance
            if matched_ref is None:
                nearest_ids = index.nearestNeighbor(geom, 5)
                best_dist, best_feat = None, None
                for fid in nearest_ids:
                    ref_geom = ref_features[fid].geometry()
                    d = ref_geom.distance(geom)
                    if best_dist is None or d < best_dist:
                        best_dist, best_feat = d, ref_features[fid]
                if best_feat is not None and (max_distance <= 0 or best_dist <= max_distance):
                    matched_ref = best_feat
                    n_fallback += 1

            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(geom)
            attrs = feat.attributes() + [None] * len(id_fields)
            out_feat.setAttributes(attrs)

            if matched_ref is not None:
                for fname in id_fields:
                    out_feat.setAttribute(fname, matched_ref.attribute(fname))
            else:
                n_unmatched += 1

            # 3. Apply manual overrides
            for match_field, match_value, target_field, target_value in overrides:
                if out_feat.fields().indexFromName(match_field) == -1:
                    continue
                if str(out_feat.attribute(match_field)) == match_value:
                    if out_feat.fields().indexFromName(target_field) != -1:
                        out_feat.setAttribute(target_field, target_value)

            sink.addFeature(out_feat)
            if total:
                feedback.setProgress(int(100 * (i + 1) / total))

        feedback.pushInfo(
            f"Matched: {n_strict} strict, {n_fallback} nearest-neighbour fallback, "
            f"{n_unmatched} unmatched."
        )
        return {self.OUTPUT: dest_id}
