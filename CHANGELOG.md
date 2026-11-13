# Changelog

All notable changes to this project are documented in this file.

---

## [1.5.1] - 2026-11-13

### Added
- "Add the layers in QGIS" option: the exported files open in an "Export YYYYMMDD_HHMM" group at the top of the Layers panel (with their style when it is kept).
- "Gather into a ZIP" option: every file of the export (shapefile parts and .qml included) goes into one `<prefix><project>.zip`; the separate files are deleted unless the layers were added in QGIS.

### Changed
- When the dialog opens, only the layers shown on the map are checked (same as the "As on screen" button), instead of all layers.

---

## [1.5.0] - 2026-11-13

### Added
- Export area: whole layer, screen extent, drawn polygon, drawn rectangle, selected features of a polygon layer, or buffer (metres) around the selected features of any layer; area preview on the map and surface shown in the dialog. A "Select" button makes the chosen layer active and starts the QGIS selection tool (QGIS selects on the active layer).
- Features crossing the area limit: kept whole or clipped (lines and polygons become multipart; Z is kept).
- "Keep layer styles" option: GeoPackage stores each layer style in the file (default style, applied when opened); Shapefile, GeoJSON, FlatGeobuf, MapInfo TAB, GML and SQLite get a `.qml` sidecar with the same name, loaded automatically by QGIS. Choice remembered between sessions.
- File name prefix: none, date (`20261113_`), date and time (`20261113_1154_`), free text, or date + text; example shown live, choice remembered between sessions (GeoPackage: prefix on the proposed file name).
- "As on screen" button to check only the layers shown on the map (visible and within their scale range).

### Changed
- New two-column layout: (1) layers on the left, grouped like the Layers panel (tri-state groups, layer icons, filter box, "n / total checked" counter); on the right (2) export area as a row of buttons, (3) format and files, (4) a highlighted "Keep layer styles" card with an on/off switch and a format-aware explanation; one-line summary above Export; log folded by default (opens on error); blocking problems shown on the status line.
- The dialog is no longer modal, so the map stays usable to draw or select the area; the layer list follows the map order and layers added/removed in the project.
- CSV and Excel exports are now limited to the area too (they were exported whole).

### Fixed
- DXF limited to an area kept neither the symbology nor the labels of the layers.
- Screen extent filter used feature bounding boxes instead of the real geometries.

---

## [1.4.0] - 2026-10-17

### Added
- GeoPackage export asks for the output file name (default: project name) and confirms before overwriting.
- Single-file DXF export (all layers in one DXF, labels kept).
- Option to export only the features within the current map view.
- Interface in 5 languages (FR / EN / ES / PT / DE).
- "Create folder" button next to the output directory.
- French CSV (`;` separator, `,` decimal, UTF-8 BOM) for Excel.

### Changed
- New About dialog (banner, badges, presentation, GitHub / LinkedIn links).
- All layers exported to GeoPackage go into a single file.
- Transparent icon background.

### Fixed
- QGIS 4 / Qt6 compatibility (scoped enums, `exec()`, `QAction` import, DXF export checks); `qgisMaximumVersion=4.99`.

---

## [1.3.1] - 2026-03-21

### Fixed
- About dialog version now read dynamically from `metadata.txt` instead of hardcoded value.
- License aligned to GNU GPL v2 in both `LICENSE` file and `metadata.txt`.

### Added
- GitHub Actions workflow for automated release to QGIS plugin repository on tag push.

---

## [1.3.0] - 2026-02-28

### Added
- **About dialog**: new "À propos / About" button in the toolbar showing the plugin logo, version, author, license (GNU GPL v2, clickable link) and GitHub repository link.

### Changed
- Plugin now registered under the **Vector** menu (`addPluginToVectorMenu`) instead of a standalone top-level menu, following QGIS plugin guidelines.
- English comments and docstrings added throughout `export_couches.py` and `export_dialog.py` to facilitate community contributions.
- Added `license=GNU GPL v2` field to `metadata.txt`.

### Fixed
- Added missing `LICENSE` file (GNU General Public License v2.0) at repository root.

### Removed
- Unused image assets (`icon2.png`, `icon3.png`, `icon4.png`, `icon5.png`) removed to keep the package clean.

---

## [1.2.0] - 2025

### Fixed
- DXF export rewritten using `QgsVectorFileWriter.writeAsVectorFormatV3` for better compatibility.
- Polygon layers are now automatically converted to boundary lines before DXF export (DXF does not support polygon fills).
- DXF export now skips attribute creation (`skipAttributeCreation = True`), as the format does not support them.

---

## [1.1.0] - 2025

### Added
- New export formats: DXF, KML, GML, FlatGeobuf, MapInfo TAB, SQLite, Excel (XLSX) — 11 formats total.
- Bilingual interface (French / English) with runtime language toggle — no restart required.

### Removed
- Hardcoded default output directory removed; user must now explicitly choose the output folder.

---

## [1.0.0] - 2025

### Added
- Initial release.
- Export vector layers to GeoJSON, Shapefile, GeoPackage, CSV.
- Optional on-the-fly reprojection (EPSG:2154, EPSG:4326, EPSG:3857).
- Layer selection with checkboxes, Select all / Deselect all buttons.
- Real-time progress bar and log area.
