import processing
import os
import re

from qgis.core import (Qgis, QgsProject,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsVectorFileWriter, QgsWkbTypes,
                       QgsVectorLayer, QgsFeatureRequest, QgsDxfExport)
from qgis.PyQt.QtCore import Qt, QFile, QIODevice
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                  QListWidget, QListWidgetItem, QPushButton,
                                  QLabel, QComboBox, QFileDialog, QLineEdit,
                                  QDialogButtonBox, QProgressBar, QTextEdit,
                                  QApplication, QSizePolicy, QFrame,
                                  QCheckBox, QInputDialog, QMessageBox)
from qgis.PyQt.QtGui import QPixmap


# ── i18n — 5 languages ───────────────────────────────────────────────────────

LANGS = ['fr', 'en', 'es', 'pt', 'de']
LANG_LABELS = {
    'fr': 'Français', 'en': 'English', 'es': 'Español',
    'pt': 'Português', 'de': 'Deutsch',
}
LANG_FLAGS = {
    'fr': '🇫🇷', 'en': '🇬🇧', 'es': '🇪🇸', 'pt': '🇵🇹', 'de': '🇩🇪',
}

TR = {
    'window_title': {
        'fr': "Export de couches vecteur",
        'en': "Vector Layer Export",
        'es': "Exportar capas vectoriales",
        'pt': "Exportar camadas vetoriais",
        'de': "Vektorlayer exportieren"},
    'layers_label': {
        'fr': "Couches à exporter :",    'en': "Layers to export:",
        'es': "Capas a exportar :",      'pt': "Camadas a exportar:",
        'de': "Zu exportierende Layer:"},
    'select_all': {
        'fr': "Tout sélectionner",  'en': "Select all",
        'es': "Seleccionar todo",   'pt': "Selecionar tudo",  'de': "Alle auswählen"},
    'select_none': {
        'fr': "Tout désélectionner", 'en': "Deselect all",
        'es': "Deseleccionar todo",  'pt': "Desmarcar tudo",  'de': "Alle abwählen"},
    'format_label': {
        'fr': "Format d'export :", 'en': "Export format:",
        'es': "Formato :",         'pt': "Formato :",         'de': "Format:"},
    'crs_label': {
        'fr': "CRS de sortie :", 'en': "Output CRS:",
        'es': "CRS de salida :", 'pt': "CRS de saída:",       'de': "Ausgabe-CRS:"},
    'output_label': {
        'fr': "Répertoire de sortie :", 'en': "Output directory:",
        'es': "Directorio de salida :", 'pt': "Diretório de saída:", 'de': "Ausgabeverzeichnis:"},
    'browse': {
        'fr': "Parcourir...", 'en': "Browse...",
        'es': "Explorar...", 'pt': "Procurar...", 'de': "Durchsuchen..."},
    'browse_title': {
        'fr': "Choisir le répertoire de sortie", 'en': "Choose output directory",
        'es': "Elegir directorio de salida",      'pt': "Escolher diretório de saída",
        'de': "Ausgabeverzeichnis wählen"},
    'waiting': {
        'fr': "En attente du lancement...", 'en': "Waiting to start...",
        'es': "Esperando inicio...",         'pt': "Aguardando início...",
        'de': "Warte auf Start..."},
    'progress_format': {
        'fr': "%v / %m couche(s)", 'en': "%v / %m layer(s)",
        'es': "%v / %m capa(s)",   'pt': "%v / %m camada(s)", 'de': "%v / %m Layer"},
    'export_btn': {
        'fr': "Exporter", 'en': "Export",
        'es': "Exportar", 'pt': "Exportar", 'de': "Exportieren"},
    'close_btn': {
        'fr': "Fermer",  'en': "Close",
        'es': "Cerrar",  'pt': "Fechar",  'de': "Schließen"},
    'about_btn': {
        'fr': "À propos", 'en': "About",
        'es': "Acerca de", 'pt': "Sobre", 'de': "Über"},
    'crs_keep': {
        'fr': "Conserver le CRS d'origine",     'en': "Keep original CRS",
        'es': "Conservar CRS original",          'pt': "Manter CRS original",
        'de': "Ursprünglichen CRS beibehalten"},
    'no_layer': {
        'fr': "⚠  Aucune couche sélectionnée.", 'en': "⚠  No layer selected.",
        'es': "⚠  Ninguna capa seleccionada.",  'pt': "⚠  Nenhuma camada selecionada.",
        'de': "⚠  Kein Layer ausgewählt."},
    'no_dir': {
        'fr': "⚠  Veuillez spécifier un répertoire de sortie.",
        'en': "⚠  Please specify an output directory.",
        'es': "⚠  Por favor especifique un directorio de salida.",
        'pt': "⚠  Por favor especifique um diretório de saída.",
        'de': "⚠  Bitte Ausgabeverzeichnis angeben."},
    'export_start': {
        'fr': "--- Début de l'export ({total} couche(s)) ---",
        'en': "--- Export started ({total} layer(s)) ---",
        'es': "--- Inicio de exportación ({total} capa(s)) ---",
        'pt': "--- Início da exportação ({total} camada(s)) ---",
        'de': "--- Export gestartet ({total} Layer) ---"},
    'in_progress': {
        'fr': "Export en cours : {name}  ({i}/{total})",
        'en': "Exporting: {name}  ({i}/{total})",
        'es': "Exportando: {name}  ({i}/{total})",
        'pt': "Exportando: {name}  ({i}/{total})",
        'de': "Exportiere: {name}  ({i}/{total})"},
    'export_ok': {
        'fr': "  ✔  OK → {path}", 'en': "  ✔  OK → {path}",
        'es': "  ✔  OK → {path}", 'pt': "  ✔  OK → {path}", 'de': "  ✔  OK → {path}"},
    'export_error': {
        'fr': "  ✘  Erreur : {error}", 'en': "  ✘  Error: {error}",
        'es': "  ✘  Error: {error}",   'pt': "  ✘  Erro: {error}", 'de': "  ✘  Fehler: {error}"},
    'export_done_ok': {
        'fr': "✔  Terminé — {total} couche(s) exportée(s) sans erreur",
        'en': "✔  Done — {total} layer(s) exported without error",
        'es': "✔  Terminado — {total} capa(s) exportada(s) sin error",
        'pt': "✔  Concluído — {total} camada(s) exportada(s) sem erro",
        'de': "✔  Fertig — {total} Layer exportiert ohne Fehler"},
    'export_done_error': {
        'fr': "⚠  Terminé — {errors} erreur(s) sur {total} couche(s)",
        'en': "⚠  Done — {errors} error(s) out of {total} layer(s)",
        'es': "⚠  Terminado — {errors} error(es) de {total} capa(s)",
        'pt': "⚠  Concluído — {errors} erro(s) de {total} camada(s)",
        'de': "⚠  Fertig — {errors} Fehler von {total} Layern"},
    'export_end': {
        'fr': "--- Export terminé ! ---",      'en': "--- Export complete! ---",
        'es': "--- ¡Exportación completa! ---", 'pt': "--- Exportação concluída! ---",
        'de': "--- Export abgeschlossen! ---"},
    'extent_option': {
        'fr': "Exporter uniquement sur l'emprise de l'écran",
        'en': "Export only within screen extent",
        'es': "Exportar solo en la extensión de pantalla",
        'pt': "Exportar apenas na extensão do ecrã",
        'de': "Nur im Kartenausschnitt exportieren"},
    'warn_no_geom': {
        'fr': "  ℹ  Note : ce format ne conserve pas la géométrie (attributs uniquement)",
        'en': "  ℹ  Note: this format does not preserve geometry (attributes only)",
        'es': "  ℹ  Nota: este formato no conserva la geometría (solo atributos)",
        'pt': "  ℹ  Nota: este formato não preserva a geometria (apenas atributos)",
        'de': "  ℹ  Hinweis: dieses Format speichert keine Geometrie (nur Attribute)"},
    'dxf_fallback': {
        'fr': "  ℹ  Paramètre ENCODING ignoré (non supporté par cette version de QGIS)",
        'en': "  ℹ  ENCODING parameter ignored (not supported by this QGIS version)",
        'es': "  ℹ  Parámetro ENCODING ignorado (no soportado por esta versión de QGIS)",
        'pt': "  ℹ  Parâmetro ENCODING ignorado (não suportado por esta versão do QGIS)",
        'de': "  ℹ  ENCODING-Parameter ignoriert (von dieser QGIS-Version nicht unterstützt)"},
    'gpkg_info': {
        'fr': "ℹ  Toutes les couches seront regroupées dans un seul fichier GeoPackage",
        'en': "ℹ  All layers will be grouped into a single GeoPackage file",
        'es': "ℹ  Todas las capas se agruparán en un único archivo GeoPackage",
        'pt': "ℹ  Todas as camadas serão agrupadas num único ficheiro GeoPackage",
        'de': "ℹ  Alle Layer werden in einer einzigen GeoPackage-Datei zusammengefasst"},
    'mkdir_btn': {
        'fr': "Créer un dossier", 'en': "Create folder",
        'es': "Crear carpeta",    'pt': "Criar pasta",   'de': "Ordner erstellen"},
    'mkdir_title': {
        'fr': "Créer un dossier", 'en': "Create folder",
        'es': "Crear carpeta",    'pt': "Criar pasta",   'de': "Ordner erstellen"},
    'mkdir_prompt': {
        'fr': "Nom du nouveau dossier :", 'en': "New folder name:",
        'es': "Nombre de la nueva carpeta :", 'pt': "Nome da nova pasta:",
        'de': "Name des neuen Ordners:"},
    'gpkg_name_title': {
        'fr': "Nom du GeoPackage", 'en': "GeoPackage name",
        'es': "Nombre del GeoPackage", 'pt': "Nome do GeoPackage",
        'de': "Name des GeoPackage"},
    'gpkg_name_prompt': {
        'fr': "Nom du fichier GeoPackage à créer :",
        'en': "Name of the GeoPackage file to create:",
        'es': "Nombre del archivo GeoPackage a crear :",
        'pt': "Nome do ficheiro GeoPackage a criar:",
        'de': "Name der zu erstellenden GeoPackage-Datei:"},
    'gpkg_overwrite': {
        'fr': "Le fichier {name} existe déjà.\nLe remplacer ?",
        'en': "The file {name} already exists.\nReplace it?",
        'es': "El archivo {name} ya existe.\n¿Reemplazarlo?",
        'pt': "O ficheiro {name} já existe.\nSubstituí-lo?",
        'de': "Die Datei {name} existiert bereits.\nErsetzen?"},
}

# CRS options: fixed labels + code, last entry uses TR['crs_keep'] per lang
CRS_FIXED = [
    ("EPSG:2154 — Lambert-93",   "EPSG:2154"),
    ("EPSG:4326 — WGS 84",       "EPSG:4326"),
    ("EPSG:3857 — Web Mercator",  "EPSG:3857"),
]

# ── Supported export formats ──────────────────────────────────────────────────

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
    "DXF (.dxf)":                      "dxf",
    "DXF — fichier unique (.dxf)":     "dxf_single",
}

NO_GEOM_FORMATS  = {"csv", "xlsx"}
DXF_FORMAT       = "dxf"
DXF_SINGLE_FORMAT = "dxf_single"


def sanitize_filename(name):
    """Replace characters illegal in file names with underscores."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


# ── About dialog (façon CanaPlan) ─────────────────────────────────────────────

PLUGIN_DIR = os.path.dirname(__file__)
ABOUT_ASSETS = os.path.join(PLUGIN_DIR, "icons", "about").replace("\\", "/")
REPO = "https://github.com/Cartoyoyo/Export_multilayers"
LINKEDIN = "https://www.linkedin.com/in/ylaloux/"
NOTICE_CSS = ("background:#FFF4E5; color:#6B4200; border:1px solid #E0A040;"
              "border-radius:4px; padding:8px;")


def _plugin_version():
    """Version read from metadata.txt (line by line: no configparser)."""
    try:
        with open(os.path.join(PLUGIN_DIR, "metadata.txt"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "?"


def _badge(href, filename):
    return f'<a href="{href}"><img src="{ABOUT_ASSETS}/{filename}"></a>'


class AboutDialog(QDialog):
    _TR = {
        'title': {'fr': "À propos d'Export Layers", 'en': "About Export Layers",
                  'es': "Acerca de Export Layers", 'pt': "Sobre o Export Layers",
                  'de': "Über Export Layers"},
        'close': {'fr': "Fermer", 'en': "Close", 'es': "Cerrar",
                  'pt': "Fechar", 'de': "Schließen"},
        'intro': {
            'fr': "Export Layers exporte en une seule fois les couches vecteur cochées du projet : "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite ou DXF, avec reprojection au choix et export limité à l'emprise affichée.",
            'en': "Export Layers exports all the checked vector layers of the project in one go: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite or DXF, with optional reprojection and export limited to the map view.",
            'es': "Export Layers exporta de una vez las capas vectoriales marcadas del proyecto: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite o DXF, con reproyección opcional y exportación limitada a la vista.",
            'pt': "O Export Layers exporta de uma só vez as camadas vetoriais marcadas do projeto: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite ou DXF, com reprojeção opcional e exportação limitada à vista.",
            'de': "Export Layers exportiert alle markierten Vektorlayer des Projekts auf einmal: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite oder DXF, mit optionaler Umprojektion und Export im Kartenausschnitt."},
        'detail': {
            'fr': "Chaque couche donne un fichier, sauf en GeoPackage et en DXF fichier unique où "
                  "toutes les couches sont regroupées dans un seul fichier. En GeoPackage, le nom du fichier est demandé au lancement de l'export.",
            'en': "Each layer gives one file, except for GeoPackage and single-file DXF, where all "
                  "layers are grouped into one file. For GeoPackage, the file name is asked when the export starts.",
            'es': "Cada capa genera un archivo, salvo en GeoPackage y DXF único, donde todas las "
                  "capas se agrupan en un solo archivo. En GeoPackage, el nombre del archivo se pide al iniciar la exportación.",
            'pt': "Cada camada gera um ficheiro, exceto em GeoPackage e DXF único, onde todas as "
                  "camadas são agrupadas num só ficheiro. Em GeoPackage, o nome do ficheiro é pedido ao iniciar a exportação.",
            'de': "Jeder Layer ergibt eine Datei, außer bei GeoPackage und DXF-Einzeldatei: dort "
                  "werden alle Layer in einer Datei zusammengefasst. Bei GeoPackage wird der Dateiname beim Exportstart abgefragt."},
        'notice': {
            'fr': "<b>À savoir</b> — CSV et Excel n'emportent que les attributs, sans géométrie. "
                  "Le DXF n'emporte que la géométrie et les étiquettes, sans attributs.",
            'en': "<b>Good to know</b> — CSV and Excel only carry attributes, without geometry. "
                  "DXF only carries geometry and labels, without attributes.",
            'es': "<b>A tener en cuenta</b> — CSV y Excel solo llevan los atributos, sin geometría. "
                  "El DXF solo lleva la geometría y las etiquetas, sin atributos.",
            'pt': "<b>A saber</b> — CSV e Excel só levam os atributos, sem geometria. "
                  "O DXF só leva a geometria e as etiquetas, sem atributos.",
            'de': "<b>Gut zu wissen</b> — CSV und Excel enthalten nur Attribute, keine Geometrie. "
                  "DXF enthält nur Geometrie und Beschriftungen, keine Attribute."},
    }

    def __init__(self, lang='fr', parent=None):
        super().__init__(parent)
        t = lambda k: self._TR[k].get(lang, self._TR[k]['en'])
        self.setWindowTitle(t('title'))
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        center = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

        # Banner: logo, name, subtitle
        banner = QLabel()
        banner.setPixmap(QPixmap(f"{ABOUT_ASSETS}/logo-full.png"))
        banner.setAlignment(center)
        layout.addWidget(banner)

        # Badges
        sep = "&nbsp;&nbsp;"
        badges = QLabel('<div style="line-height:220%">'
                        + _badge("https://qgis.org", "badge-qgis.png") + sep
                        + _badge(REPO, "badge-formats.png") + sep
                        + _badge(f"{REPO}#readme", "badge-doc.png") + "</div>")
        badges.setAlignment(center)
        badges.setWordWrap(True)
        badges.setOpenExternalLinks(True)
        layout.addWidget(badges)

        layout.addWidget(self._separator())

        # Presentation, justified
        for key in ('intro', 'detail'):
            text = QLabel(t(key))
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignmentFlag.AlignJustify)
            layout.addWidget(text)

        notice = QLabel(t('notice'))
        notice.setWordWrap(True)
        notice.setAlignment(Qt.AlignmentFlag.AlignJustify)
        notice.setStyleSheet(NOTICE_CSS)
        layout.addWidget(notice)

        layout.addWidget(self._separator())

        # Author + version (link to the changelog), GitHub / LinkedIn badges
        author = QLabel(f'<b>Yoan Laloux</b><br><a href="{REPO}/blob/main/README.md#changelog">'
                        f'version {_plugin_version()}</a>')
        author.setAlignment(center)
        author.setOpenExternalLinks(True)
        layout.addWidget(author)

        links = QLabel(_badge(REPO, "badge-github.png") + sep + _badge(LINKEDIN, "badge-linkedin.png"))
        links.setAlignment(center)
        links.setOpenExternalLinks(True)
        layout.addWidget(links)

        layout.addWidget(self._separator())

        row = QHBoxLayout()
        row.addStretch()
        btn_close = QPushButton(t('close'))
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_close)
        row.addStretch()
        layout.addLayout(row)
        self.adjustSize()

    @staticmethod
    def _separator():
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep


# ── Main export dialog ────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    """Main dialog: layer selection, format/CRS/directory picker, progress bar and log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang = 'fr'
        self.setMinimumWidth(620)
        self.setMinimumHeight(560)

        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        # ── Top bar: language combo + about button ────────────────────────────
        top_layout = QHBoxLayout()
        top_layout.addStretch()

        self.combo_lang = QComboBox()
        for code in LANGS:
            self.combo_lang.addItem(f"{LANG_FLAGS[code]}  {LANG_LABELS[code]}")
        self.combo_lang.setFixedHeight(28)
        self.combo_lang.setMinimumWidth(130)
        self.combo_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        top_layout.addWidget(self.combo_lang)

        self.btn_about = QPushButton()
        self.btn_about.setFixedWidth(90)
        self.btn_about.setFixedHeight(28)
        self.btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_about.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #95a5a6; }
        """)
        self.btn_about.clicked.connect(self.show_about)
        top_layout.addWidget(self.btn_about)

        layout.addLayout(top_layout)

        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # ── Layer list ────────────────────────────────────────────────────────
        self.lbl_layers = QLabel()
        layout.addWidget(self.lbl_layers)

        self.layer_list = QListWidget()
        self.layer_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layers = {}
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                label = f"{layer.name()}  [{layer.dataProvider().name()}]"
                item  = QListWidgetItem(label)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.layer_list.addItem(item)
                self.layers[label] = layer
        layout.addWidget(self.layer_list)

        # ── Select all / deselect all ─────────────────────────────────────────
        btn_sel_layout = QHBoxLayout()
        self.btn_all  = QPushButton()
        self.btn_none = QPushButton()
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        btn_sel_layout.addWidget(self.btn_all)
        btn_sel_layout.addWidget(self.btn_none)
        layout.addLayout(btn_sel_layout)

        # ── Format + CRS side by side ─────────────────────────────────────────
        fmt_crs_layout = QHBoxLayout()
        fmt_crs_layout.setSpacing(8)

        fmt_col = QVBoxLayout()
        fmt_col.setSpacing(2)
        self.lbl_format = QLabel()
        self.format_combo = QComboBox()
        for fmt in FORMATS:
            self.format_combo.addItem(fmt)
        self.lbl_gpkg_info = QLabel()
        self.lbl_gpkg_info.setStyleSheet(
            "color: #1a6b3a; font-style: italic; font-size: 10px; padding: 2px 0;"
        )
        self.lbl_gpkg_info.setWordWrap(True)
        self.lbl_gpkg_info.setVisible(False)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        fmt_col.addWidget(self.lbl_format)
        fmt_col.addWidget(self.format_combo)
        fmt_col.addWidget(self.lbl_gpkg_info)

        crs_col = QVBoxLayout()
        crs_col.setSpacing(2)
        self.lbl_crs = QLabel()
        self.crs_combo = QComboBox()
        crs_col.addWidget(self.lbl_crs)
        crs_col.addWidget(self.crs_combo)

        fmt_crs_layout.addLayout(fmt_col)
        fmt_crs_layout.addLayout(crs_col)
        layout.addLayout(fmt_crs_layout)

        # ── Output directory picker ───────────────────────────────────────────
        self.lbl_output = QLabel()
        layout.addWidget(self.lbl_output)
        dir_layout = QHBoxLayout()
        self.dir_edit   = QLineEdit()
        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self.browse_dir)
        self.btn_mkdir  = QPushButton()
        self.btn_mkdir.clicked.connect(self.create_folder)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(self.btn_browse)
        dir_layout.addWidget(self.btn_mkdir)
        layout.addLayout(dir_layout)

        # ── Option : export by screen extent ─────────────────────────────
        self.chk_extent = QCheckBox()
        self.chk_extent.setChecked(False)
        layout.addWidget(self.chk_extent)

        # ── Progress status + bar ─────────────────────────────────────────────
        self.progress_status = QLabel()
        layout.addWidget(self.progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # ── Log area ──────────────────────────────────────────────────────────
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(100)
        layout.addWidget(self.log_area)

        # ── Export / Close buttons ────────────────────────────────────────────
        self.buttons    = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_export = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_close  = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.run_export)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        self.apply_language()

    # ── Language management ───────────────────────────────────────────────────

    def t(self, key, **kwargs):
        text = TR[key].get(self.lang, TR[key]['en'])
        if kwargs:
            text = text.format(**kwargs)
        return text

    def _on_lang_changed(self, index):
        crs_index = self.crs_combo.currentIndex()
        self.lang  = LANGS[index]
        self.apply_language()
        self.crs_combo.setCurrentIndex(crs_index)

    def apply_language(self):
        self.setWindowTitle(self.t('window_title'))
        self.lbl_layers.setText(self.t('layers_label'))
        self.btn_all.setText(self.t('select_all'))
        self.btn_none.setText(self.t('select_none'))
        self.lbl_format.setText(self.t('format_label'))
        self.lbl_crs.setText(self.t('crs_label'))
        self.lbl_output.setText(self.t('output_label'))
        self.btn_browse.setText(self.t('browse'))
        self.progress_status.setText(self.t('waiting'))
        self.progress_bar.setFormat(self.t('progress_format'))
        self.chk_extent.setText(self.t('extent_option'))
        self.btn_export.setText(self.t('export_btn'))
        self.btn_close.setText(self.t('close_btn'))
        self.btn_about.setText(self.t('about_btn'))
        self.btn_mkdir.setText(self.t('mkdir_btn'))
        self.lbl_gpkg_info.setText(self.t('gpkg_info'))
        self._on_format_changed(self.format_combo.currentIndex())

        current_idx = self.crs_combo.currentIndex()
        self.crs_combo.clear()
        self._crs_values = []
        for label, code in CRS_FIXED:
            self.crs_combo.addItem(label)
            self._crs_values.append(code)
        self.crs_combo.addItem(self.t('crs_keep'))
        self._crs_values.append(None)
        if 0 <= current_idx < self.crs_combo.count():
            self.crs_combo.setCurrentIndex(current_idx)

    def show_about(self):
        AboutDialog(lang=self.lang, parent=self).exec()

    def _on_format_changed(self, index):
        fmt = FORMATS.get(self.format_combo.currentText(), "")
        self.lbl_gpkg_info.setVisible(fmt == "gpkg")

    # ── Helper methods ────────────────────────────────────────────────────────

    def select_all(self):
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.CheckState.Checked)

    def select_none(self):
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, self.t('browse_title'))
        if folder:
            self.dir_edit.setText(folder)

    def create_folder(self):
        parent = self.dir_edit.text().strip()
        if not parent:
            parent = QFileDialog.getExistingDirectory(self, self.t('browse_title'))
            if not parent:
                return
            self.dir_edit.setText(parent)
        name, ok = QInputDialog.getText(self, self.t('mkdir_title'), self.t('mkdir_prompt'))
        if ok and name.strip():
            new_dir = os.path.join(parent, name.strip())
            os.makedirs(new_dir, exist_ok=True)
            self.dir_edit.setText(new_dir)

    def _ask_gpkg_path(self, output_dir):
        """Ask the GeoPackage file name; return its full path or None if cancelled."""
        default = sanitize_filename(QgsProject.instance().baseName() or "export")
        while True:
            name, ok = QInputDialog.getText(
                self, self.t('gpkg_name_title'), self.t('gpkg_name_prompt'),
                QLineEdit.EchoMode.Normal, default
            )
            if not ok:
                return None
            name = name.strip()
            if name.lower().endswith(".gpkg"):
                name = name[:-5].strip()
            name = sanitize_filename(name)
            if not name:
                continue
            gpkg_path = os.path.join(output_dir, name + ".gpkg")
            if not os.path.exists(gpkg_path):
                return gpkg_path
            answer = QMessageBox.question(
                self, self.t('gpkg_name_title'),
                self.t('gpkg_overwrite', name=name + ".gpkg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if answer == QMessageBox.StandardButton.Yes:
                return gpkg_path
            default = name

    def get_selected_layers(self):
        selected = []
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(self.layers[item.text()])
        return selected

    def log(self, message):
        self.log_area.append(message)
        QApplication.processEvents()

    def set_controls_enabled(self, enabled):
        self.layer_list.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.crs_combo.setEnabled(enabled)
        self.dir_edit.setEnabled(enabled)
        self.chk_extent.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.combo_lang.setEnabled(enabled)

    # ── Extent filter ─────────────────────────────────────────────────────────

    def _filter_by_extent(self, layer):
        """Return a memory layer containing only features within the canvas extent."""
        from qgis.utils import iface as qgis_iface

        canvas     = qgis_iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()
        extent     = canvas.extent()

        # Transform extent to layer CRS if needed
        if canvas_crs != layer.crs():
            transform = QgsCoordinateTransform(
                canvas_crs, layer.crs(), QgsProject.instance()
            )
            extent = transform.transformBoundingBox(extent)

        geom_type = QgsWkbTypes.displayString(layer.wkbType())
        mem_layer = QgsVectorLayer(
            f"{geom_type}?crs={layer.crs().authid()}",
            layer.name(), "memory"
        )
        provider = mem_layer.dataProvider()
        provider.addAttributes(layer.fields().toList())
        mem_layer.updateFields()

        request = QgsFeatureRequest().setFilterRect(extent)
        provider.addFeatures(list(layer.getFeatures(request)))
        mem_layer.updateExtents()
        return mem_layer

    # ── CSV French format export ──────────────────────────────────────────────

    def _export_csv_french(self, layer, output_path):
        """Export layer to CSV with French conventions: ';' separator, ',' decimal."""
        import csv
        fields = layer.fields()
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([field.name() for field in fields])
            for feature in layer.getFeatures():
                row = []
                for idx in range(len(fields)):
                    val = feature[idx]
                    if isinstance(val, float):
                        row.append(str(val).replace('.', ','))
                    elif val is None:
                        row.append('')
                    else:
                        row.append(val)
                writer.writerow(row)

    # ── DXF export — pattern canonique (inspiré de BET_HUMIDE/tools/dxf_export.py)

    def _dxf_write(self, layers_list, output_path, crs_code):
        """Écrit un DXF 2018 en suivant le pattern canonique QgsDxfExport.

        Ordre des appels : setMapSettings (transformContext uniquement) →
        addLayers → setSymbologyScale → setSymbologyExport → setDestinationCrs
        → setForce2d → setFlags → writeToFile (CP1252).

        layers_list : list[QgsVectorLayer], dans l'ordre bottom→top (déjà inversé).
        """
        project = QgsProject.instance()

        from qgis.core import QgsMapSettings as _QgsMapSettings
        ms = _QgsMapSettings()
        ms.setTransformContext(project.transformContext())

        export = QgsDxfExport()
        export.setMapSettings(ms)
        export.addLayers([QgsDxfExport.DxfLayer(l) for l in layers_list])
        export.setSymbologyScale(500.0)

        # SymbolLayerSymbology = fidélité maximale
        # (QGIS ≥ 3.30 / 4 : Qgis.FeatureSymbologyExport.PerSymbolLayer)
        sym = getattr(getattr(Qgis, 'FeatureSymbologyExport', None), 'PerSymbolLayer', None)
        if sym is None:
            sym = (getattr(QgsDxfExport, 'SymbolLayerSymbology', None)
                   or getattr(getattr(QgsDxfExport, 'SymbologyExport', None),
                              'SymbolLayerSymbology', None))
        if sym is not None:
            export.setSymbologyExport(sym)

        dest_crs = (QgsCoordinateReferenceSystem(crs_code)
                    if crs_code else project.crs())
        export.setDestinationCrs(dest_crs)

        if hasattr(export, 'setForce2d'):
            export.setForce2d(True)

        flags_cls = (getattr(QgsDxfExport, 'Flags', None)
                     or getattr(QgsDxfExport, 'Flag', None))
        if flags_cls is not None and hasattr(export, 'setFlags'):
            try:
                export.setFlags(flags_cls())
            except (TypeError, ValueError):
                pass

        f = QFile(output_path)
        if not f.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Truncate):
            raise Exception(f"Impossible d'ouvrir {output_path} en écriture")
        try:
            result = export.writeToFile(f, 'CP1252')
        finally:
            f.close()

        if result != QgsDxfExport.ExportResult.Success:
            raise Exception(f"QgsDxfExport : {result}")

    def export_dxf(self, layer, output_path, crs_code):
        """Export DXF d'une couche unique (appelé par la boucle principale)."""
        has_labels = layer.labelsEnabled() and layer.labeling()
        self.log("  ℹ  DXF : étiquettes ✔" if has_labels
                 else "  ℹ  DXF : pas d'étiquette configurée")
        self._dxf_write([layer], output_path, crs_code)

    # ── DXF single-file export ────────────────────────────────────────────────

    def _run_export_dxf_single(self, layers, output_dir, crs_code):
        project_name = QgsProject.instance().baseName() or "export"
        output_path  = os.path.join(output_dir, sanitize_filename(project_name) + ".dxf")

        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)
        self.log(self.t('export_start', total=len(layers)))

        # kept_alive : empêche Python de GC les couches mémoire pendant l'export
        kept_alive = []
        export_layers = []
        for layer in reversed(layers):   # bottom→top = ordre d'écriture DXF
            if self.chk_extent.isChecked():
                lyr = self._filter_by_extent(layer)
                kept_alive.append(lyr)
            else:
                lyr = layer
            export_layers.append(lyr)
            has_labels = layer.labelsEnabled() and layer.labeling()
            self.log(f"  + {layer.name()}" + (" [étiquettes ✔]" if has_labels else ""))

        try:
            self._dxf_write(export_layers, output_path, crs_code)
            self.log(self.t('export_ok', path=output_path))
            self.progress_status.setText(self.t('export_done_ok', total=len(layers)))
        except Exception as e:
            self.log(self.t('export_error', error=e))
            self.progress_status.setText(self.t('export_done_error', errors=1, total=1))
        finally:
            kept_alive.clear()

        self.progress_bar.setValue(1)
        self.log(self.t('export_end'))
        self.set_controls_enabled(True)

    # ── Main export orchestration ─────────────────────────────────────────────

    def run_export(self):
        selected_layers = self.get_selected_layers()
        fmt        = FORMATS[self.format_combo.currentText()]
        output_dir = self.dir_edit.text().strip()
        crs_code   = self._crs_values[self.crs_combo.currentIndex()]

        if not selected_layers:
            self.log(self.t('no_layer'))
            return
        if not output_dir:
            self.log(self.t('no_dir'))
            return

        # ── GeoPackage : demander le nom du fichier unique ─────────────────
        if fmt == "gpkg":
            gpkg_path = self._ask_gpkg_path(output_dir)
            if not gpkg_path:
                return

        os.makedirs(output_dir, exist_ok=True)
        self.set_controls_enabled(False)
        self.log_area.clear()

        # ── DXF fichier unique : chemin dédié ─────────────────────────────
        if fmt == DXF_SINGLE_FORMAT:
            self._run_export_dxf_single(selected_layers, output_dir, crs_code)
            return

        total = len(selected_layers)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        errors = 0

        self.log(self.t('export_start', total=total))

        gpkg_layer_count = 0   # nombre de couches déjà écrites dans le GPKG

        for i, layer in enumerate(selected_layers):
            safe_name   = sanitize_filename(layer.name())
            output_path = os.path.join(output_dir, safe_name + "." + fmt)

            self.progress_status.setText(
                self.t('in_progress', name=layer.name(), i=i+1, total=total)
            )
            self.log(f"▶  {layer.name()}  [{layer.dataProvider().name()}]")

            if fmt in NO_GEOM_FORMATS:
                self.log(self.t('warn_no_geom'))

            QApplication.processEvents()

            try:
                export_layer = (
                    self._filter_by_extent(layer)
                    if self.chk_extent.isChecked() and fmt not in NO_GEOM_FORMATS
                    else layer
                )

                if fmt == DXF_FORMAT:
                    self.export_dxf(export_layer, output_path, crs_code)

                elif fmt == "csv":
                    self._export_csv_french(export_layer, output_path)

                elif fmt == "gpkg":
                    # QgsVectorFileWriter direct : seule méthode fiable pour
                    # ajouter plusieurs couches dans un même fichier GPKG
                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.driverName   = "GPKG"
                    options.layerName    = safe_name
                    options.fileEncoding = "UTF-8"
                    options.actionOnExistingFile = (
                        QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
                        if gpkg_layer_count == 0
                        else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                    )
                    if crs_code:
                        options.ct = QgsCoordinateTransform(
                            export_layer.crs(),
                            QgsCoordinateReferenceSystem(crs_code),
                            QgsProject.instance()
                        )
                    if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
                        err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                            export_layer, gpkg_path,
                            QgsProject.instance().transformContext(), options
                        )
                    else:
                        err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                            export_layer, gpkg_path,
                            QgsProject.instance().transformContext(), options
                        )
                    if err != QgsVectorFileWriter.WriterError.NoError:
                        raise Exception(msg)
                    gpkg_layer_count += 1
                    output_path = gpkg_path   # pour le message OK

                elif crs_code:
                    processing.run("native:reprojectlayer", {
                        'INPUT':      export_layer,
                        'TARGET_CRS': QgsCoordinateReferenceSystem(crs_code),
                        'OUTPUT':     output_path
                    })
                else:
                    processing.run("native:savefeatures", {
                        'INPUT': export_layer, 'OUTPUT': output_path
                    })

                self.log(self.t('export_ok', path=output_path))
            except Exception as e:
                self.log(self.t('export_error', error=e))
                errors += 1

            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

        if errors == 0:
            self.progress_status.setText(self.t('export_done_ok', total=total))
        else:
            self.progress_status.setText(self.t('export_done_error', errors=errors, total=total))

        self.log(self.t('export_end'))
        self.set_controls_enabled(True)
        self.btn_close.setText(self.t('close_btn'))
