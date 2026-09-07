No boundary data is bundled in this plugin (a full-resolution India
district GeoPackage is large, and you already maintain a corrected one
for India Drought Monitor with the Ladakh/J&K state_id split resolved).

Point the plugin at it via Plugins \u2192 India Boundary Toolkit \u2192
"Set Boundary GeoPackage Path\u2026". It expects a GeoPackage with one or
more layers (e.g. `states`, `districts`) carrying whatever ID/name
fields you want available for the "Assign Admin IDs by Boundary"
algorithm.

If you'd rather ship a lightweight simplified copy inside the plugin
for portability, drop it here as `india_boundaries.gpkg` and change
`load_boundaries()` in `boundary_toolkit.py` to fall back to this file
when no path is configured.
