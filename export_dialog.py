import processing
import os
import re

from qgis.core import (QgsProject, QgsMapLayer,
                       QgsCoordinateReferenceSystem,
                       QgsVectorFileWriter, QgsWkbTypes)
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                  QListWidget, QListWidgetItem, QPushButton,
                                  QLabel, QComboBox, QFileDialog, QLineEdit,
                                  QDialogButtonBox, QProgressBar, QTextEdit,
                                  QApplication, QSizePolicy, QFrame)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QPixmap


# ── Translation dictionary (FR / EN) ─────────────────────────────────────────

TRANSLATIONS = {
    'fr': {
        'window_title':    "Export de couches vecteur",
        'language_btn':    "🇬🇧  English",
        'layers_label':    "Couches à exporter :",
        'select_all':      "Tout sélectionner",
        'select_none':     "Tout désélectionner",
        'format_label':    "Format d'export :",
        'crs_label':       "CRS de sortie :",
        'output_label':    "Répertoire de sortie :",
        'browse':          "Parcourir...",
        'browse_title':    "Choisir le répertoire de sortie",
        'progress_label':  "Progression :",
        'waiting':         "En attente du lancement...",
        'progress_format': "%v / %m couche(s)",
        'log_label':       "Journal :",
        'export_btn':      "Exporter",
        'close_btn':       "Fermer",
        'about_btn':       "À propos",
        'crs_options': {
            "EPSG:2154 — Lambert-93":     "EPSG:2154",
            "EPSG:4326 — WGS 84":         "EPSG:4326",
            "EPSG:3857 — Web Mercator":   "EPSG:3857",
            "Conserver le CRS d'origine": None,
        },
        'no_layer':          "⚠  Aucune couche sélectionnée.",
        'no_dir':            "⚠  Veuillez spécifier un répertoire de sortie.",
        'export_start':      "--- Début de l'export ({total} couche(s)) ---",
        'in_progress':       "Export en cours : {name}  ({i}/{total})",
        'export_ok':         "  ✔  OK → {path}",
        'export_error':      "  ✘  Erreur : {error}",
        'export_done_ok':    "✔  Terminé — {total} couche(s) exportée(s) sans erreur",
        'export_done_error': "⚠  Terminé — {errors} erreur(s) sur {total} couche(s)",
        'export_end':        "--- Export terminé ! ---",
        'warn_no_geom':      "  ℹ  Note : ce format ne conserve pas la géométrie (attributs uniquement)",
        'dxf_fallback':      "  ℹ  Paramètre ENCODING ignoré (non supporté par cette version de QGIS)",
    },
    'en': {
        'window_title':    "Vector Layer Export",
        'language_btn':    "🇫🇷  Français",
        'layers_label':    "Layers to export:",
        'select_all':      "Select all",
        'select_none':     "Deselect all",
        'format_label':    "Export format:",
        'crs_label':       "Output CRS:",
        'output_label':    "Output directory:",
        'browse':          "Browse...",
        'browse_title':    "Choose output directory",
        'progress_label':  "Progress:",
        'waiting':         "Waiting to start...",
        'progress_format': "%v / %m layer(s)",
        'log_label':       "Log:",
        'export_btn':      "Export",
        'close_btn':       "Close",
        'about_btn':       "About",
        'crs_options': {
            "EPSG:2154 — Lambert-93":   "EPSG:2154",
            "EPSG:4326 — WGS 84":       "EPSG:4326",
            "EPSG:3857 — Web Mercator": "EPSG:3857",
            "Keep original CRS":        None,
        },
        'no_layer':          "⚠  No layer selected.",
        'no_dir':            "⚠  Please specify an output directory.",
        'export_start':      "--- Export started ({total} layer(s)) ---",
        'in_progress':       "Exporting: {name}  ({i}/{total})",
        'export_ok':         "  ✔  OK → {path}",
        'export_error':      "  ✘  Error: {error}",
        'export_done_ok':    "✔  Done — {total} layer(s) exported without error",
        'export_done_error': "⚠  Done — {errors} error(s) out of {total} layer(s)",
        'export_end':        "--- Export complete! ---",
        'warn_no_geom':      "  ℹ  Note: this format does not preserve geometry (attributes only)",
        'dxf_fallback':      "  ℹ  ENCODING parameter ignored (not supported by this QGIS version)",
    }
}

# ── Supported export formats: display label → OGR driver extension ────────────

FORMATS = {
    "GeoJSON (.geojson)":  "geojson",
    "Shapefile (.shp)":    "shp",
    "GeoPackage (.gpkg)":  "gpkg",
    "CSV (.csv)":          "csv",
    "Excel (.xlsx)":       "xlsx",
    "KML (.kml)":          "kml",
    "GML (.gml)":          "gml",
    "FlatGeobuf (.fgb)":   "fgb",
    "MapInfo TAB (.tab)":  "tab",
    "SQLite (.sqlite)":    "sqlite",
    "DXF (.dxf)":          "dxf",
}

# Formats that do not preserve geometry — a warning is shown in the log
NO_GEOM_FORMATS = {"csv", "xlsx"}

# DXF requires a dedicated export path (polygon-to-line conversion + no attributes)
DXF_FORMAT = "dxf"


def sanitize_filename(name):
    """Replace characters illegal in file names with underscores."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


# ── About dialog ──────────────────────────────────────────────────────────────

class AboutDialog(QDialog):
    """Simple modal dialog showing plugin info: logo, license and GitHub link."""

    def __init__(self, lang='fr', parent=None):
        super().__init__(parent)
        self.setWindowTitle("À propos" if lang == 'fr' else "About")
        self.setFixedWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            lbl_logo = QLabel()
            pixmap = QPixmap(logo_path).scaledToWidth(160, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pixmap)
            lbl_logo.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_logo)

        # Titre
        lbl_name = QLabel("Export Couches Vecteur\nVector Layer Export")
        font_title = QFont()
        font_title.setBold(True)
        font_title.setPointSize(12)
        lbl_name.setFont(font_title)
        lbl_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_name)

        # Version
        lbl_version = QLabel("Version 1.2.0")
        lbl_version.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_version)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Auteur
        lbl_author = QLabel("Yoan Laloux — Vichy Communauté\ny.laloux@vichy-communaute.fr")
        lbl_author.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_author)

        # Licence
        lbl_license = QLabel(
            '<a href="https://www.gnu.org/licenses/old-licenses/gpl-2.0.html">'
            'GNU General Public License v2.0</a>'
        )
        lbl_license.setOpenExternalLinks(True)
        lbl_license.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_license)

        # Dépôt GitHub
        lbl_github = QLabel(
            '<a href="https://github.com/Cartoyoyo/Export_multilayers">'
            'github.com/Cartoyoyo/Export_multilayers</a>'
        )
        lbl_github.setOpenExternalLinks(True)
        lbl_github.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_github)

        # Bouton fermer
        btn_close = QPushButton("Fermer" if lang == 'fr' else "Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)


# ── Main export dialog ────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    """Main dialog: layer selection, format/CRS/directory picker, progress bar and log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang = 'fr'  # Default language: French
        self.setMinimumWidth(620)
        self.setMinimumHeight(720)

        layout = QVBoxLayout()
        layout.setSpacing(6)

        # ── Top bar: title label + language toggle + about button ────────────
        top_layout = QHBoxLayout()

        self.lbl_title = QLabel()
        font_title = QFont()
        font_title.setBold(True)
        font_title.setPointSize(11)
        self.lbl_title.setFont(font_title)
        top_layout.addWidget(self.lbl_title)

        top_layout.addStretch()

        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(130)
        self.btn_lang.setFixedHeight(28)
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3d5166;
            }
        """)
        self.btn_lang.clicked.connect(self.toggle_language)
        top_layout.addWidget(self.btn_lang)

        self.btn_about = QPushButton()
        self.btn_about.setFixedWidth(90)
        self.btn_about.setFixedHeight(28)
        self.btn_about.setCursor(Qt.PointingHandCursor)
        self.btn_about.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        self.btn_about.clicked.connect(self.show_about)
        top_layout.addWidget(self.btn_about)

        layout.addLayout(top_layout)

        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # ── Layer list: populate with all vector layers from the current project ──
        self.lbl_layers = QLabel()
        layout.addWidget(self.lbl_layers)

        self.layer_list = QListWidget()
        self.layer_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.layers = {}  # Maps list item label → QgsVectorLayer
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                label = f"{layer.name()}  [{layer.dataProvider().name()}]"
                item  = QListWidgetItem(label)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.layer_list.addItem(item)
                self.layers[label] = layer
        layout.addWidget(self.layer_list)

        # ── Select all / deselect all buttons ────────────────
        btn_sel_layout = QHBoxLayout()
        self.btn_all  = QPushButton()
        self.btn_none = QPushButton()
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        btn_sel_layout.addWidget(self.btn_all)
        btn_sel_layout.addWidget(self.btn_none)
        layout.addLayout(btn_sel_layout)

        # ── Export format dropdown ────────────────────────────
        self.lbl_format = QLabel()
        layout.addWidget(self.lbl_format)
        self.format_combo = QComboBox()
        for fmt in FORMATS:
            self.format_combo.addItem(fmt)
        layout.addWidget(self.format_combo)

        # ── Output CRS dropdown ───────────────────────────────
        self.lbl_crs = QLabel()
        layout.addWidget(self.lbl_crs)
        self.crs_combo = QComboBox()
        layout.addWidget(self.crs_combo)

        # ── Output directory picker ───────────────────────────
        self.lbl_output = QLabel()
        layout.addWidget(self.lbl_output)
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setText("")
        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self.browse_dir)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

        # ── Progress bar and status label ────────────────────
        self.lbl_progress = QLabel()
        layout.addWidget(self.lbl_progress)

        self.progress_status = QLabel()
        layout.addWidget(self.progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # ── Read-only log area ────────────────────────────────
        self.lbl_log = QLabel()
        layout.addWidget(self.lbl_log)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(130)
        layout.addWidget(self.log_area)

        # ── Export / Close buttons ────────────────────────────
        self.buttons    = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.btn_export = self.buttons.button(QDialogButtonBox.Ok)
        self.btn_close  = self.buttons.button(QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.run_export)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

        # Apply default language strings to all widgets
        self.apply_language()

    # ── Language management ───────────────────────────────────

    def t(self, key, **kwargs):
        """Return the translated string for the given key, with optional format args."""
        text = TRANSLATIONS[self.lang][key]
        if kwargs:
            text = text.format(**kwargs)
        return text

    def toggle_language(self):
        """Switch between French and English, preserving the current CRS selection."""
        crs_index = self.crs_combo.currentIndex()
        self.lang  = 'en' if self.lang == 'fr' else 'fr'
        self.apply_language()
        self.crs_combo.setCurrentIndex(crs_index)

    def apply_language(self):
        """Update all widget labels to the current language."""
        tr = TRANSLATIONS[self.lang]

        self.setWindowTitle(tr['window_title'])
        self.lbl_title.setText(tr['window_title'])
        self.btn_lang.setText(tr['language_btn'])

        self.lbl_layers.setText(tr['layers_label'])
        self.btn_all.setText(tr['select_all'])
        self.btn_none.setText(tr['select_none'])
        self.lbl_format.setText(tr['format_label'])
        self.lbl_crs.setText(tr['crs_label'])
        self.lbl_output.setText(tr['output_label'])
        self.btn_browse.setText(tr['browse'])
        self.lbl_progress.setText(tr['progress_label'])
        self.progress_status.setText(tr['waiting'])
        self.progress_bar.setFormat(tr['progress_format'])
        self.lbl_log.setText(tr['log_label'])
        self.btn_export.setText(tr['export_btn'])
        self.btn_close.setText(tr['close_btn'])
        self.btn_about.setText(tr['about_btn'])

        current_idx = self.crs_combo.currentIndex()
        self.crs_combo.clear()
        self.crs_options = tr['crs_options']
        for crs_label in self.crs_options:
            self.crs_combo.addItem(crs_label)
        if current_idx >= 0:
            self.crs_combo.setCurrentIndex(current_idx)

    def show_about(self):
        dialog = AboutDialog(lang=self.lang, parent=self)
        dialog.exec_()

    # ── Helper methods ────────────────────────────────────────

    def select_all(self):
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.Checked)

    def select_none(self):
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.Unchecked)

    def browse_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.t('browse_title')
        )
        if folder:
            self.dir_edit.setText(folder)

    def get_selected_layers(self):
        selected = []
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(self.layers[item.text()])
        return selected

    def log(self, message):
        self.log_area.append(message)
        QApplication.processEvents()

    def set_controls_enabled(self, enabled):
        """Enable or disable input controls during export to prevent concurrent runs."""
        self.layer_list.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.crs_combo.setEnabled(enabled)
        self.dir_edit.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.btn_lang.setEnabled(enabled)

    # ── DXF export ────────────────────────────────────────────

    def export_dxf(self, layer, output_path, crs_code):
        """
        Export a layer to DXF via QgsVectorFileWriter.
        Polygon layers are converted to their boundary lines first,
        because DXF only stores geometry (no attributes).
        """
        self.log("  ℹ  Note : DXF exporte uniquement la géométrie (attributs ignorés)")

        # Convert polygons to boundary lines — DXF does not support polygon fills
        geom_type = QgsWkbTypes.geometryType(layer.wkbType())
        if geom_type == QgsWkbTypes.PolygonGeometry:
            self.log("  ℹ  Conversion polygones → contours (lignes)")
            result = processing.run("native:polygonstolines", {
                'INPUT': layer,
                'OUTPUT': 'memory:'
            })
            export_layer = result['OUTPUT']
        else:
            export_layer = layer

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "DXF"
        options.fileEncoding = "UTF-8"
        options.attributes = []
        options.skipAttributeCreation = True
        if crs_code:
            options.destCrs = QgsCoordinateReferenceSystem(crs_code)

        transform_context = QgsProject.instance().transformContext()
        error, error_msg, new_filename, new_layer = QgsVectorFileWriter.writeAsVectorFormatV3(
            export_layer,
            output_path,
            transform_context,
            options
        )

        if error != QgsVectorFileWriter.NoError:
            raise Exception(error_msg if error_msg else f"Erreur DXF (code {error})")

    # ── Main export orchestration ─────────────────────────────

    def run_export(self):
        """Iterate over selected layers and export each one to the chosen format."""
        selected_layers = self.get_selected_layers()
        fmt        = FORMATS[self.format_combo.currentText()]
        output_dir = self.dir_edit.text().strip()
        crs_code   = self.crs_options[self.crs_combo.currentText()]

        if not selected_layers:
            self.log(self.t('no_layer'))
            return

        if not output_dir:
            self.log(self.t('no_dir'))
            return

        os.makedirs(output_dir, exist_ok=True)

        total = len(selected_layers)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.set_controls_enabled(False)
        self.log_area.clear()
        errors = 0

        self.log(self.t('export_start', total=total))

        for i, layer in enumerate(selected_layers):
            safe_name   = sanitize_filename(layer.name())
            output_path = os.path.join(output_dir, safe_name + "." + fmt)

            self.progress_status.setText(
                self.t('in_progress', name=layer.name(), i=i+1, total=total)
            )
            self.log(f"▶  {layer.name()}  [{layer.dataProvider().name()}]")

            # Warn when the chosen format does not support geometry
            if fmt in NO_GEOM_FORMATS:
                self.log(self.t('warn_no_geom'))

            QApplication.processEvents()

            try:
                if fmt == DXF_FORMAT:
                    # DXF requires a dedicated path (polygon conversion + no attributes)
                    self.export_dxf(layer, output_path, crs_code)

                elif crs_code:
                    # Reproject on-the-fly then write to the target format
                    processing.run("native:reprojectlayer", {
                        'INPUT':      layer,
                        'TARGET_CRS': QgsCoordinateReferenceSystem(crs_code),
                        'OUTPUT':     output_path
                    })

                else:
                    # Standard OGR export, keeping the original CRS
                    processing.run("native:savefeatures", {
                        'INPUT':  layer,
                        'OUTPUT': output_path
                    })

                self.log(self.t('export_ok', path=output_path))

            except Exception as e:
                self.log(self.t('export_error', error=e))
                errors += 1

            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

        # ── Final summary ─────────────────────────────────────
        if errors == 0:
            self.progress_status.setText(
                self.t('export_done_ok', total=total)
            )
        else:
            self.progress_status.setText(
                self.t('export_done_error', errors=errors, total=total)
            )

        self.log(self.t('export_end'))
        self.set_controls_enabled(True)
        self.btn_close.setText(self.t('close_btn'))