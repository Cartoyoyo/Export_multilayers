# Changelog

All notable changes to this project are documented in this file.

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
