# India Boundary & CRS Toolkit (QGIS plugin)

Two Processing algorithms plus a toolbar action, aimed at the recurring
friction points from rebuilding the IDM district/grid pipeline:

## Reproject / Fix Source CRS
Reprojects a layer to a target CRS, with an optional **source CRS
override**. Use this when a file's declared CRS is missing or wrong
(a real issue with some LCC-projected district sources) \u2014 tell QGIS
the true source CRS instead of trusting the file's own metadata.

## Assign Admin IDs by Boundary
Spatial-joins ID/name fields from a reference boundary layer onto
points or small polygons. Tries strict containment first, then falls
back to nearest-boundary-by-distance (a native `QgsSpatialIndex`
equivalent of the cKDTree fallback used in `build_districts_v2.py`) for
features a strict join misses \u2014 small districts, coastal/border grid
cells. Supports a manual override table for known special cases, e.g.:

```
district_name=Ladakh->state_id=38;district_name=Jammu and Kashmir->state_id=15
```

## Load India Boundaries (toolbar action)
Loads a GeoPackage of state/district boundaries into the project. No
data is bundled \u2014 point it at your own maintained GeoPackage via
Plugins \u2192 India Boundary Toolkit \u2192 "Set Boundary GeoPackage Path\u2026"
(see `data/README.md`).

## Install (dev mode)

```
ln -s $(pwd)/india_boundary_toolkit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/india_boundary_toolkit
```

Enable it in QGIS \u2192 Plugins \u2192 Manage and Install Plugins \u2192 Installed.

## Notes / things to adapt

- `assign_admin_ids.py`'s override syntax is deliberately minimal
  (`match_field=value->target_field=value`, `;`-separated). Swap in a
  small JSON/CSV override file instead if the rule set grows.
- The nearest-neighbour fallback in `assign_admin_ids.py` checks 5
  spatial-index candidates before picking the closest by true distance
  \u2014 bump that if you have very irregular/sparse reference polygons.
- No `icon.png` is bundled; drop one into the plugin root to have it
  picked up by both the toolbar action and the Processing provider.
