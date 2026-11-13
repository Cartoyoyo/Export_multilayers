import processing
import os
import re
import glob
import time
import zipfile
from datetime import datetime

from qgis.core import (Qgis, QgsProject, QgsSettings, QgsMapLayerStyle,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsVectorFileWriter, QgsGeometry, QgsPointXY,
                       QgsVectorLayer, QgsDxfExport, QgsMapLayerProxyModel)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt, QFile, QIODevice, QTimer, QEvent
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                  QListWidget, QListWidgetItem, QPushButton,
                                  QLabel, QComboBox, QFileDialog, QLineEdit,
                                  QDialogButtonBox, QProgressBar, QTextEdit,
                                  QApplication, QSizePolicy, QFrame,
                                  QInputDialog, QMessageBox, QDoubleSpinBox, QCheckBox,
                                  QRadioButton, QButtonGroup, QToolButton,
                                  QTreeWidget, QTreeWidgetItem, QGridLayout)
from qgis.PyQt.QtGui import QPixmap, QPainter, QColor
from qgis.PyQt.QtCore import QRectF
try:
    from qgis.core import QgsIconUtils          # QGIS ≥ 3.20
except ImportError:                             # pragma: no cover
    QgsIconUtils = None

from .zone_tools import (POLYGON_TYPE, ZoneMapTool, make_rubber_band,
                         remove_rubber_band, zone_area_m2, metric_crs_for,
                         transform_geometry, filter_layer_by_zone)


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

    # ── Layer quick selection ────────────────────────────────────────────────
    'select_visible': {
        'fr': "Comme à l'écran",   'en': "As on screen",
        'es': "Como en pantalla",  'pt': "Como no ecrã",   'de': "Wie auf der Karte"},
    'select_visible_tip': {
        'fr': "Coche les couches affichées sur la carte (cochées dans le panneau Couches et dans leur plage d'échelle)",
        'en': "Checks the layers shown on the map (checked in the Layers panel and within their scale range)",
        'es': "Marca las capas mostradas en el mapa (marcadas en el panel Capas y dentro de su rango de escala)",
        'pt': "Marca as camadas mostradas no mapa (marcadas no painel Camadas e dentro do seu intervalo de escala)",
        'de': "Markiert die auf der Karte angezeigten Layer (im Layerbedienfeld aktiviert und im Maßstabsbereich)"},

    # ── Export zone ──────────────────────────────────────────────────────────
    'zone_label': {
        'fr': "Zone d'export :",  'en': "Export area:",
        'es': "Zona de exportación:", 'pt': "Zona de exportação:", 'de': "Exportbereich:"},
    'zone_all': {
        'fr': "Toute la couche",  'en': "Whole layer",
        'es': "Toda la capa",     'pt': "Toda a camada",   'de': "Ganzer Layer"},
    'zone_screen': {
        'fr': "Emprise de l'écran", 'en': "Screen extent",
        'es': "Extensión de pantalla", 'pt': "Extensão do ecrã", 'de': "Kartenausschnitt"},
    'zone_polygon': {
        'fr': "Polygone dessiné",  'en': "Drawn polygon",
        'es': "Polígono dibujado", 'pt': "Polígono desenhado", 'de': "Gezeichnetes Polygon"},
    'zone_rectangle': {
        'fr': "Rectangle dessiné",  'en': "Drawn rectangle",
        'es': "Rectángulo dibujado", 'pt': "Retângulo desenhado", 'de': "Gezeichnetes Rechteck"},
    'zone_selection': {
        'fr': "Entités sélectionnées", 'en': "Selected features",
        'es': "Entidades seleccionadas", 'pt': "Elementos selecionados",
        'de': "Ausgewählte Objekte"},
    'zone_buffer': {
        'fr': "Tampon autour de la sélection", 'en': "Buffer around selection",
        'es': "Búfer alrededor de la selección", 'pt': "Buffer à volta da seleção",
        'de': "Puffer um die Auswahl"},
    'draw_btn': {
        'fr': "✏  Dessiner", 'en': "✏  Draw", 'es': "✏  Dibujar",
        'pt': "✏  Desenhar", 'de': "✏  Zeichnen"},
    'pick_btn': {
        'fr': "⬚  Sélectionner", 'en': "⬚  Select", 'es': "⬚  Seleccionar",
        'pt': "⬚  Selecionar", 'de': "⬚  Auswählen"},
    'pick_tip': {
        'fr': "Rend cette couche active et lance l'outil de sélection de QGIS",
        'en': "Makes this layer active and starts the QGIS selection tool",
        'es': "Activa esta capa e inicia la herramienta de selección de QGIS",
        'pt': "Ativa esta camada e inicia a ferramenta de seleção do QGIS",
        'de': "Macht diesen Layer aktiv und startet das QGIS-Auswahlwerkzeug"},
    'hint_select': {
        'fr': "Cliquez ou tracez un rectangle sur « {layer} » (Maj = ajouter, Ctrl = retirer). Clic droit, Entrée ou « Terminé » pour revenir à la fenêtre.",
        'en': "Click or drag a rectangle on “{layer}” (Shift = add, Ctrl = remove). Right click, Enter or “Done” to return to the dialog.",
        'es': "Haga clic o trace un rectángulo sobre «{layer}» (Mayús = añadir, Ctrl = quitar). Clic derecho, Intro o «Terminado» para volver a la ventana.",
        'pt': "Clique ou trace um retângulo sobre «{layer}» (Shift = adicionar, Ctrl = remover). Clique direito, Enter ou «Concluído» para voltar à janela.",
        'de': "Klicken oder Rechteck ziehen auf „{layer}“ (Umschalt = hinzufügen, Strg = entfernen). Rechtsklick, Eingabe oder „Fertig“ kehrt zum Fenster zurück."},
    'pick_done': {
        'fr': "✔  Terminé", 'en': "✔  Done", 'es': "✔  Terminado",
        'pt': "✔  Concluído", 'de': "✔  Fertig"},
    'hint_hidden': {
        'fr': " Couche masquée : cochez-la pour voir ce que vous sélectionnez.",
        'en': " Hidden layer: check it to see what you select.",
        'es': " Capa oculta: márquela para ver lo que selecciona.",
        'pt': " Camada oculta: marque-a para ver o que seleciona.",
        'de': " Ausgeblendeter Layer: aktivieren, um die Auswahl zu sehen."},
    'zone_layer_tip': {
        'fr': "Couche dont les entités sélectionnées forment la zone",
        'en': "Layer whose selected features make the area",
        'es': "Capa cuyas entidades seleccionadas forman la zona",
        'pt': "Camada cujos elementos selecionados formam a zona",
        'de': "Layer, dessen ausgewählte Objekte den Bereich bilden"},
    'buffer_tip': {
        'fr': "Distance du tampon en mètres", 'en': "Buffer distance in metres",
        'es': "Distancia del búfer en metros", 'pt': "Distância do buffer em metros",
        'de': "Pufferabstand in Metern"},
    'zone_whole': {
        'fr': "Objets entiers", 'en': "Whole features",
        'es': "Objetos enteros", 'pt': "Objetos inteiros", 'de': "Ganze Objekte"},
    'zone_whole_tip': {
        'fr': "Exporte entier chaque objet qui touche la zone",
        'en': "Exports every feature touching the area as a whole",
        'es': "Exporta entero cada objeto que toca la zona",
        'pt': "Exporta inteiro cada objeto que toca a zona",
        'de': "Exportiert jedes Objekt, das den Bereich berührt, vollständig"},
    'zone_clip': {
        'fr': "Découpés à la limite", 'en': "Clipped at the limit",
        'es': "Recortados en el límite", 'pt': "Recortados no limite",
        'de': "An der Grenze zugeschnitten"},
    'zone_clip_tip': {
        'fr': "Coupe les géométries à la limite de la zone (CSV et Excel : sans effet)",
        'en': "Cuts geometries at the area limit (no effect on CSV and Excel)",
        'es': "Corta las geometrías en el límite de la zona (sin efecto en CSV y Excel)",
        'pt': "Corta as geometrias no limite da zona (sem efeito em CSV e Excel)",
        'de': "Schneidet Geometrien an der Bereichsgrenze (ohne Wirkung bei CSV und Excel)"},
    'zone_not_drawn': {
        'fr': "aucune zone dessinée", 'en': "no area drawn",
        'es': "ninguna zona dibujada", 'pt': "nenhuma zona desenhada",
        'de': "kein Bereich gezeichnet"},
    'zone_info_area': {
        'fr': "Zone : {area}", 'en': "Area: {area}", 'es': "Zona: {area}",
        'pt': "Zona: {area}", 'de': "Bereich: {area}"},
    'zone_info_sel': {
        'fr': "{n} entité(s) — {area}", 'en': "{n} feature(s) — {area}",
        'es': "{n} entidad(es) — {area}", 'pt': "{n} elemento(s) — {area}",
        'de': "{n} Objekt(e) — {area}"},
    'zone_no_layer': {
        'fr': "choisissez une couche", 'en': "choose a layer",
        'es': "elija una capa", 'pt': "escolha uma camada", 'de': "Layer wählen"},
    'zone_no_selection': {
        'fr': "aucune entité sélectionnée dans « {layer} »",
        'en': "no feature selected in “{layer}”",
        'es': "ninguna entidad seleccionada en «{layer}»",
        'pt': "nenhum elemento selecionado em «{layer}»",
        'de': "kein Objekt in „{layer}“ ausgewählt"},
    'zone_not_polygon': {
        'fr': "« {layer} » n'est pas une couche de polygones : utilisez le tampon",
        'en': "“{layer}” is not a polygon layer: use the buffer",
        'es': "«{layer}» no es una capa de polígonos: use el búfer",
        'pt': "«{layer}» não é uma camada de polígonos: use o buffer",
        'de': "„{layer}“ ist kein Polygonlayer: Puffer verwenden"},
    'zone_bad_distance': {
        'fr': "distance du tampon nulle", 'en': "buffer distance is zero",
        'es': "distancia del búfer nula", 'pt': "distância do buffer nula",
        'de': "Pufferabstand ist null"},
    'zone_invalid': {
        'fr': "zone vide ou invalide", 'en': "empty or invalid area",
        'es': "zona vacía o no válida", 'pt': "zona vazia ou inválida",
        'de': "leerer oder ungültiger Bereich"},
    'hint_polygon': {
        'fr': "Cliquez les sommets ; clic droit ou double-clic pour fermer, Retour arrière pour effacer le dernier point, Échap pour abandonner.",
        'en': "Click the vertices; right click or double click to close, Backspace to remove the last point, Esc to cancel.",
        'es': "Haga clic en los vértices; clic derecho o doble clic para cerrar, Retroceso para borrar el último punto, Esc para cancelar.",
        'pt': "Clique nos vértices; clique direito ou duplo clique para fechar, Retrocesso para apagar o último ponto, Esc para cancelar.",
        'de': "Eckpunkte anklicken; Rechtsklick oder Doppelklick zum Schließen, Rücktaste löscht den letzten Punkt, Esc bricht ab."},
    'hint_rectangle': {
        'fr': "Cliquez-glissez pour tracer le rectangle, Échap pour abandonner.",
        'en': "Click and drag to draw the rectangle, Esc to cancel.",
        'es': "Haga clic y arrastre para dibujar el rectángulo, Esc para cancelar.",
        'pt': "Clique e arraste para desenhar o retângulo, Esc para cancelar.",
        'de': "Klicken und ziehen, um das Rechteck zu zeichnen, Esc bricht ab."},
    'zone_log': {
        'fr': "Zone : {desc} — {mode}", 'en': "Area: {desc} — {mode}",
        'es': "Zona: {desc} — {mode}", 'pt': "Zona: {desc} — {mode}",
        'de': "Bereich: {desc} — {mode}"},
    'zone_count': {
        'fr': "  ℹ  {kept} objet(s) dans la zone",
        'en': "  ℹ  {kept} feature(s) in the area",
        'es': "  ℹ  {kept} objeto(s) en la zona",
        'pt': "  ℹ  {kept} objeto(s) na zona",
        'de': "  ℹ  {kept} Objekt(e) im Bereich"},
    'zone_skip_nogeom': {
        'fr': "  ℹ  Couche sans géométrie : exportée entière",
        'en': "  ℹ  Layer without geometry: exported whole",
        'es': "  ℹ  Capa sin geometría: exportada entera",
        'pt': "  ℹ  Camada sem geometria: exportada inteira",
        'de': "  ℹ  Layer ohne Geometrie: vollständig exportiert"},
    'sec_layers': {
        'fr': "Couches", 'en': "Layers", 'es': "Capas", 'pt': "Camadas", 'de': "Layer"},
    'sec_zone': {
        'fr': "Zone d'export", 'en': "Export area", 'es': "Zona de exportación",
        'pt': "Zona de exportação", 'de': "Exportbereich"},
    'sec_files': {
        'fr': "Format et fichiers", 'en': "Format and files", 'es': "Formato y archivos",
        'pt': "Formato e ficheiros", 'de': "Format und Dateien"},
    'lbl_fmt': {'fr': "Format", 'en': "Format", 'es': "Formato", 'pt': "Formato", 'de': "Format"},
    'lbl_crs': {'fr': "CRS", 'en': "CRS", 'es': "CRS", 'pt': "CRS", 'de': "KBS"},
    'lbl_dir': {'fr': "Dossier", 'en': "Folder", 'es': "Carpeta", 'pt': "Pasta", 'de': "Ordner"},
    'lbl_prefix_short': {'fr': "Préfixe", 'en': "Prefix", 'es': "Prefijo", 'pt': "Prefixo", 'de': "Präfix"},
    'filter_ph': {
        'fr': "🔍  Filtrer les couches…", 'en': "🔍  Filter layers…", 'es': "🔍  Filtrar capas…",
        'pt': "🔍  Filtrar camadas…", 'de': "🔍  Layer filtern…"},
    'count_checked': {
        'fr': "{n} / {total} cochée(s)", 'en': "{n} / {total} checked", 'es': "{n} / {total} marcada(s)",
        'pt': "{n} / {total} marcada(s)", 'de': "{n} / {total} markiert"},
    'select_all_short': {'fr': "Tout", 'en': "All", 'es': "Todo", 'pt': "Tudo", 'de': "Alle"},
    'select_none_short': {'fr': "Aucune", 'en': "None", 'es': "Ninguna", 'pt': "Nenhuma", 'de': "Keine"},
    'zs_all': {'fr': "Tout", 'en': "All", 'es': "Todo", 'pt': "Tudo", 'de': "Alles"},
    'zs_screen': {'fr': "🖥 Écran", 'en': "🖥 Screen", 'es': "🖥 Pantalla", 'pt': "🖥 Ecrã", 'de': "🖥 Ausschnitt"},
    'zs_polygon': {'fr': "✏ Polygone", 'en': "✏ Polygon", 'es': "✏ Polígono", 'pt': "✏ Polígono", 'de': "✏ Polygon"},
    'zs_rectangle': {'fr': "▭ Rectangle", 'en': "▭ Rectangle", 'es': "▭ Rectángulo", 'pt': "▭ Retângulo", 'de': "▭ Rechteck"},
    'zs_selection': {'fr': "⬚ Sélection", 'en': "⬚ Selection", 'es': "⬚ Selección", 'pt': "⬚ Seleção", 'de': "⬚ Auswahl"},
    'zs_buffer': {'fr': "◎ Tampon", 'en': "◎ Buffer", 'es': "◎ Búfer", 'pt': "◎ Buffer", 'de': "◎ Puffer"},
    'zone_all_info': {
        'fr': "Toutes les entités des couches cochées", 'en': "All features of the checked layers",
        'es': "Todas las entidades de las capas marcadas", 'pt': "Todos os elementos das camadas marcadas",
        'de': "Alle Objekte der markierten Layer"},
    'log_btn': {'fr': "Journal", 'en': "Log", 'es': "Registro", 'pt': "Registo", 'de': "Protokoll"},
    'browse_tip': {
        'fr': "Choisir le dossier de sortie", 'en': "Choose the output folder",
        'es': "Elegir la carpeta de salida", 'pt': "Escolher a pasta de saída", 'de': "Ausgabeordner wählen"},
    'style_on': {'fr': "ACTIVÉ", 'en': "ON", 'es': "ACTIVADO", 'pt': "ATIVADO", 'de': "AN"},
    'style_off': {'fr': "DÉSACTIVÉ", 'en': "OFF", 'es': "DESACTIVADO", 'pt': "DESATIVADO", 'de': "AUS"},
    'style_always': {'fr': "TOUJOURS", 'en': "ALWAYS", 'es': "SIEMPRE", 'pt': "SEMPRE", 'de': "IMMER"},
    'style_na': {'fr': "INDISPONIBLE", 'en': "N/A", 'es': "NO DISPONIBLE", 'pt': "INDISPONÍVEL", 'de': "N. V."},
    'style_msg_gpkg': {
        'fr': "Symbologie et étiquettes enregistrées dans le GeoPackage : la couche s'ouvre directement avec son style.",
        'en': "Symbology and labels stored in the GeoPackage: the layer opens with its style.",
        'es': "Simbología y etiquetas guardadas en el GeoPackage: la capa se abre con su estilo.",
        'pt': "Simbologia e etiquetas guardadas no GeoPackage: a camada abre com o seu estilo.",
        'de': "Symbologie und Beschriftungen im GeoPackage gespeichert: der Layer öffnet sich mit seinem Stil."},
    'style_msg_qml': {
        'fr': "Un fichier .qml du même nom est écrit à côté de chaque fichier ; QGIS le relit tout seul.",
        'en': "A .qml file with the same name is written next to each file; QGIS loads it automatically.",
        'es': "Se escribe un archivo .qml con el mismo nombre junto a cada archivo; QGIS lo carga solo.",
        'pt': "Um ficheiro .qml com o mesmo nome é escrito ao lado de cada ficheiro; o QGIS carrega-o sozinho.",
        'de': "Neben jeder Datei wird eine gleichnamige .qml-Datei geschrieben; QGIS lädt sie automatisch."},
    'style_msg_dxf': {
        'fr': "Le DXF garde toujours la symbologie et les étiquettes (entités DAO).",
        'en': "DXF always keeps the symbology and labels (CAD entities).",
        'es': "El DXF siempre conserva la simbología y las etiquetas (entidades CAD).",
        'pt': "O DXF mantém sempre a simbologia e as etiquetas (entidades CAD).",
        'de': "DXF behält immer Symbologie und Beschriftungen (CAD-Objekte)."},
    'style_msg_na': {
        'fr': "Indisponible pour ce format : il ne garde pas de style.",
        'en': "Not available for this format: it keeps no style.",
        'es': "No disponible para este formato: no conserva estilo.",
        'pt': "Indisponível para este formato: não mantém estilo.",
        'de': "Für dieses Format nicht verfügbar: es speichert keinen Stil."},
    'style_msg_off': {
        'fr': "Les fichiers sortiront avec le style par défaut de QGIS.",
        'en': "Files will open with the default QGIS style.",
        'es': "Los archivos se abrirán con el estilo por defecto de QGIS.",
        'pt': "Os ficheiros abrirão com o estilo predefinido do QGIS.",
        'de': "Die Dateien öffnen sich mit dem QGIS-Standardstil."},
    'recap_layers': {
        'fr': "{n} couche(s)", 'en': "{n} layer(s)", 'es': "{n} capa(s)", 'pt': "{n} camada(s)", 'de': "{n} Layer"},
    'recap_one_file': {
        'fr': "1 fichier {ext}", 'en': "1 {ext} file", 'es': "1 archivo {ext}", 'pt': "1 ficheiro {ext}",
        'de': "1 {ext}-Datei"},
    'recap_files': {
        'fr': "{n} fichier(s) {ext}", 'en': "{n} {ext} file(s)", 'es': "{n} archivo(s) {ext}",
        'pt': "{n} ficheiro(s) {ext}", 'de': "{n} {ext}-Datei(en)"},
    'recap_style': {
        'fr': "🎨 style conservé", 'en': "🎨 style kept", 'es': "🎨 estilo conservado",
        'pt': "🎨 estilo mantido", 'de': "🎨 Stil beibehalten"},
    'example_layer': {
        'fr': "couche", 'en': "layer", 'es': "capa", 'pt': "camada", 'de': "layer"},
    'dxf_labels_yes': {
        'fr': "  ℹ  DXF : étiquettes ✔", 'en': "  ℹ  DXF: labels ✔", 'es': "  ℹ  DXF: etiquetas ✔",
        'pt': "  ℹ  DXF: etiquetas ✔", 'de': "  ℹ  DXF: Beschriftungen ✔"},
    'dxf_labels_no': {
        'fr': "  ℹ  DXF : pas d'étiquette configurée", 'en': "  ℹ  DXF: no labels configured",
        'es': "  ℹ  DXF: sin etiquetas configuradas", 'pt': "  ℹ  DXF: sem etiquetas configuradas",
        'de': "  ℹ  DXF: keine Beschriftung eingerichtet"},
    'dxf_labels_tag': {
        'fr': " [étiquettes ✔]", 'en': " [labels ✔]", 'es': " [etiquetas ✔]",
        'pt': " [etiquetas ✔]", 'de': " [Beschriftungen ✔]"},
    'file_open_error': {
        'fr': "Impossible d'ouvrir {path} en écriture", 'en': "Cannot open {path} for writing",
        'es': "No se puede abrir {path} para escritura", 'pt': "Não é possível abrir {path} para escrita",
        'de': "{path} kann nicht zum Schreiben geöffnet werden"},
    'add_project': {
        'fr': "Ajouter les couches dans QGIS", 'en': "Add the layers in QGIS",
        'es': "Añadir las capas en QGIS", 'pt': "Adicionar as camadas no QGIS",
        'de': "Layer in QGIS hinzufügen"},
    'add_project_on': {
        'fr': "Les fichiers exportés s'ouvrent dans un groupe « Export {date} » en haut du panneau Couches.",
        'en': "Exported files open in an “Export {date}” group at the top of the Layers panel.",
        'es': "Los archivos exportados se abren en un grupo «Export {date}» arriba del panel Capas.",
        'pt': "Os ficheiros exportados abrem num grupo «Export {date}» no topo do painel Camadas.",
        'de': "Die exportierten Dateien öffnen sich in einer Gruppe „Export {date}“ oben im Layerbedienfeld."},
    'add_project_off': {
        'fr': "Les fichiers sont seulement écrits sur le disque.",
        'en': "Files are only written to disk.",
        'es': "Los archivos solo se escriben en el disco.",
        'pt': "Os ficheiros são apenas escritos no disco.",
        'de': "Die Dateien werden nur auf die Festplatte geschrieben."},
    'added_group': {
        'fr': "Export {date}", 'en': "Export {date}", 'es': "Export {date}",
        'pt': "Export {date}", 'de': "Export {date}"},
    'added_log': {
        'fr': "  ➕  {n} couche(s) ajoutée(s) dans QGIS, groupe « {group} »",
        'en': "  ➕  {n} layer(s) added in QGIS, group “{group}”",
        'es': "  ➕  {n} capa(s) añadida(s) en QGIS, grupo «{group}»",
        'pt': "  ➕  {n} camada(s) adicionada(s) no QGIS, grupo «{group}»",
        'de': "  ➕  {n} Layer in QGIS hinzugefügt, Gruppe „{group}“"},
    'added_fail': {
        'fr': "  ⚠  Impossible d'ouvrir {name} dans QGIS",
        'en': "  ⚠  Cannot open {name} in QGIS",
        'es': "  ⚠  No se puede abrir {name} en QGIS",
        'pt': "  ⚠  Não é possível abrir {name} no QGIS",
        'de': "  ⚠  {name} kann nicht in QGIS geöffnet werden"},
    'recap_added': {
        'fr': "➕ ajoutées dans QGIS", 'en': "➕ added in QGIS", 'es': "➕ añadidas en QGIS",
        'pt': "➕ adicionadas no QGIS", 'de': "➕ in QGIS hinzugefügt"},
    'zip_title': {
        'fr': "Rassembler dans un ZIP", 'en': "Gather into a ZIP", 'es': "Reunir en un ZIP",
        'pt': "Reunir num ZIP", 'de': "In einem ZIP zusammenfassen"},
    'zip_on': {
        'fr': "Tous les fichiers de l'export sont réunis dans {name} ; les fichiers séparés sont supprimés.",
        'en': "All files of the export are gathered in {name}; the separate files are deleted.",
        'es': "Todos los archivos de la exportación se reúnen en {name}; los archivos sueltos se eliminan.",
        'pt': "Todos os ficheiros da exportação são reunidos em {name}; os ficheiros soltos são apagados.",
        'de': "Alle Dateien des Exports werden in {name} zusammengefasst; die einzelnen Dateien werden gelöscht."},
    'zip_on_keep': {
        'fr': "Tous les fichiers sont réunis dans {name} ; ils restent aussi à côté pour les couches ajoutées dans QGIS.",
        'en': "All files are gathered in {name}; they also stay alongside for the layers added in QGIS.",
        'es': "Todos los archivos se reúnen en {name}; también quedan al lado para las capas añadidas en QGIS.",
        'pt': "Todos os ficheiros são reunidos em {name}; ficam também ao lado para as camadas adicionadas no QGIS.",
        'de': "Alle Dateien werden in {name} zusammengefasst; sie bleiben auch daneben für die in QGIS hinzugefügten Layer."},
    'zip_off': {
        'fr': "Les fichiers restent séparés dans le dossier.",
        'en': "Files stay separate in the folder.",
        'es': "Los archivos quedan separados en la carpeta.",
        'pt': "Os ficheiros ficam separados na pasta.",
        'de': "Die Dateien bleiben einzeln im Ordner."},
    'zip_log': {
        'fr': "  🗜  {n} fichier(s) réunis dans {name}", 'en': "  🗜  {n} file(s) gathered in {name}",
        'es': "  🗜  {n} archivo(s) reunidos en {name}", 'pt': "  🗜  {n} ficheiro(s) reunidos em {name}",
        'de': "  🗜  {n} Datei(en) in {name} zusammengefasst"},
    'zip_error': {
        'fr': "  ⚠  ZIP non créé : {error}", 'en': "  ⚠  ZIP not created: {error}",
        'es': "  ⚠  ZIP no creado: {error}", 'pt': "  ⚠  ZIP não criado: {error}",
        'de': "  ⚠  ZIP nicht erstellt: {error}"},
    'recap_zip': {
        'fr': "🗜 dans un ZIP", 'en': "🗜 in a ZIP", 'es': "🗜 en un ZIP", 'pt': "🗜 num ZIP", 'de': "🗜 als ZIP"},
    'keep_style': {
        'fr': "Conserver le style des couches", 'en': "Keep layer styles",
        'es': "Conservar el estilo de las capas", 'pt': "Manter o estilo das camadas",
        'de': "Layerstile beibehalten"},
    'keep_style_tip': {
        'fr': "GeoPackage : style enregistré dans le fichier et appliqué à l'ouverture.\n"
              "Shapefile, GeoJSON, FlatGeobuf, TAB, GML, SQLite : fichier .qml du même nom à côté, relu automatiquement par QGIS.\n"
              "Sans objet en CSV, Excel et KML ; le DXF garde déjà la symbologie.",
        'en': "GeoPackage: style stored in the file and applied when opened.\n"
              "Shapefile, GeoJSON, FlatGeobuf, TAB, GML, SQLite: .qml file with the same name alongside, loaded automatically by QGIS.\n"
              "Not available for CSV, Excel and KML; DXF already keeps the symbology.",
        'es': "GeoPackage: estilo guardado en el archivo y aplicado al abrirlo.\n"
              "Shapefile, GeoJSON, FlatGeobuf, TAB, GML, SQLite: archivo .qml con el mismo nombre al lado, cargado automáticamente por QGIS.\n"
              "No disponible en CSV, Excel y KML; el DXF ya conserva la simbología.",
        'pt': "GeoPackage: estilo guardado no ficheiro e aplicado ao abrir.\n"
              "Shapefile, GeoJSON, FlatGeobuf, TAB, GML, SQLite: ficheiro .qml com o mesmo nome ao lado, carregado automaticamente pelo QGIS.\n"
              "Não disponível em CSV, Excel e KML; o DXF já mantém a simbologia.",
        'de': "GeoPackage: Stil in der Datei gespeichert und beim Öffnen angewendet.\n"
              "Shapefile, GeoJSON, FlatGeobuf, TAB, GML, SQLite: gleichnamige .qml-Datei daneben, von QGIS automatisch geladen.\n"
              "Nicht verfügbar für CSV, Excel und KML; DXF behält die Symbologie bereits."},
    'style_saved_gpkg': {
        'fr': "  🎨  Style enregistré dans le GeoPackage",
        'en': "  🎨  Style stored in the GeoPackage",
        'es': "  🎨  Estilo guardado en el GeoPackage",
        'pt': "  🎨  Estilo guardado no GeoPackage",
        'de': "  🎨  Stil im GeoPackage gespeichert"},
    'style_saved_qml': {
        'fr': "  🎨  Style enregistré : {name}", 'en': "  🎨  Style saved: {name}",
        'es': "  🎨  Estilo guardado: {name}", 'pt': "  🎨  Estilo guardado: {name}",
        'de': "  🎨  Stil gespeichert: {name}"},
    'style_error': {
        'fr': "  ⚠  Style non enregistré : {error}", 'en': "  ⚠  Style not saved: {error}",
        'es': "  ⚠  Estilo no guardado: {error}", 'pt': "  ⚠  Estilo não guardado: {error}",
        'de': "  ⚠  Stil nicht gespeichert: {error}"},
    'prefix_label': {
        'fr': "Préfixe :", 'en': "Prefix:", 'es': "Prefijo:", 'pt': "Prefixo:", 'de': "Präfix:"},
    'prefix_none': {
        'fr': "Aucun", 'en': "None", 'es': "Ninguno", 'pt': "Nenhum", 'de': "Keins"},
    'prefix_date': {
        'fr': "Date ({date})", 'en': "Date ({date})", 'es': "Fecha ({date})",
        'pt': "Data ({date})", 'de': "Datum ({date})"},
    'prefix_datetime': {
        'fr': "Date et heure ({date})", 'en': "Date and time ({date})", 'es': "Fecha y hora ({date})",
        'pt': "Data e hora ({date})", 'de': "Datum und Uhrzeit ({date})"},
    'prefix_text': {
        'fr': "Texte", 'en': "Text", 'es': "Texto", 'pt': "Texto", 'de': "Text"},
    'prefix_date_text': {
        'fr': "Date + texte", 'en': "Date + text", 'es': "Fecha + texto",
        'pt': "Data + texto", 'de': "Datum + Text"},
    'prefix_placeholder': {
        'fr': "texte du préfixe (ex. : PROJET)", 'en': "prefix text (e.g. PROJECT)",
        'es': "texto del prefijo (ej.: PROYECTO)", 'pt': "texto do prefixo (ex.: PROJETO)",
        'de': "Präfixtext (z. B. PROJEKT)"},
    'prefix_tip': {
        'fr': "Ajouté devant le nom de chaque fichier exporté ; date AAAAMMJJ (et heure HHMM) pour un tri chronologique",
        'en': "Added in front of each exported file name; date YYYYMMDD (and time HHMM) so files sort chronologically",
        'es': "Se añade delante del nombre de cada archivo exportado; fecha AAAAMMDD (y hora HHMM) para un orden cronológico",
        'pt': "Adicionado antes do nome de cada ficheiro exportado; data AAAAMMDD (e hora HHMM) para ordenação cronológica",
        'de': "Wird jedem exportierten Dateinamen vorangestellt; Datum JJJJMMTT (und Uhrzeit HHMM) für chronologische Sortierung"},
    'prefix_example': {
        'fr': "→ {name}", 'en': "→ {name}", 'es': "→ {name}", 'pt': "→ {name}", 'de': "→ {name}"},
    'prefix_empty': {
        'fr': "⚠  Préfixe : saisissez le texte ou choisissez « Aucun »",
        'en': "⚠  Prefix: type the text or choose “None”",
        'es': "⚠  Prefijo: escriba el texto o elija «Ninguno»",
        'pt': "⚠  Prefixo: escreva o texto ou escolha «Nenhum»",
        'de': "⚠  Präfix: Text eingeben oder „Keins“ wählen"},
    'prefix_log': {
        'fr': "Préfixe des fichiers : {prefix}", 'en': "File prefix: {prefix}",
        'es': "Prefijo de archivos: {prefix}", 'pt': "Prefixo dos ficheiros: {prefix}",
        'de': "Dateipräfix: {prefix}"},
    'zone_error': {
        'fr': "⚠  Zone d'export : {error}", 'en': "⚠  Export area: {error}",
        'es': "⚠  Zona de exportación: {error}", 'pt': "⚠  Zona de exportação: {error}",
        'de': "⚠  Exportbereich: {error}"},
}

# Formats able to keep the layer style: in the file (gpkg) or as a .qml sidecar
STYLE_FORMATS = {"gpkg", "shp", "geojson", "fgb", "tab", "gml", "sqlite"}

PREFIX_MODES = ['none', 'date', 'datetime', 'text', 'date_text']
DATE_FMT     = "%Y%m%d"
DATETIME_FMT = "%Y%m%d_%H%M"
SETTINGS_KEY = "Export_multilayers/"

ZONE_MODES      = ['all', 'screen', 'polygon', 'rectangle', 'selection', 'buffer']
DRAWN_MODES     = ('polygon', 'rectangle')
SELECTION_MODES = ('selection', 'buffer')
LAYER_ID_ROLE   = Qt.ItemDataRole.UserRole


class ZoneError(Exception):
    """Export zone cannot be built (nothing drawn, empty selection…)."""


def _layer_filter(name):
    """Layer combo filter valid on QGIS 3 (QgsMapLayerProxyModel) and QGIS 4 (Qgis.LayerFilter)."""
    lf = getattr(Qgis, 'LayerFilter', None)
    if lf is not None and hasattr(lf, name):
        return getattr(lf, name)
    return getattr(QgsMapLayerProxyModel, name)


def _iface():
    from qgis.utils import iface
    return iface


class ToggleSwitch(QCheckBox):
    """Checkbox drawn as an on/off switch (Qt5 / Qt6)."""

    ON, OFF = QColor("#2e8b57"), QColor("#b9c2c9")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.forced_on = False          # drawn on without changing the value (DXF)
        self.unavailable = False        # drawn off whatever the value (CSV, Excel, KML)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        on = (self.isChecked() or self.forced_on) and not self.unavailable
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        track = QColor(self.ON if on else self.OFF)
        if not self.isEnabled():
            track.setAlpha(120)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 2, 40, 18), 9, 9)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QRectF(20 if on else 2, 3, 16, 16))
        painter.end()


class StyleCard(QFrame):
    """Framed block around the 'keep style' switch; a click anywhere toggles it."""

    def __init__(self, switch, parent=None):
        super().__init__(parent)
        self.switch = switch
        self.setObjectName("styleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.switch.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.switch.toggle()
        super().mousePressEvent(event)

    def set_state(self, state):
        """'on' / 'off' / 'na'."""
        css = {
            'on':  "#styleCard{border:2px solid #2e8b57;border-radius:6px;background:rgba(46,139,87,0.10);}",
            'off': "#styleCard{border:2px solid #c9c9c9;border-radius:6px;}",
            'na':  "#styleCard{border:2px dashed #c9c9c9;border-radius:6px;}",
        }[state]
        self.setStyleSheet(css)


def _badge_label(text, color="#1a6b3a"):
    lbl = QLabel(text)
    lbl.setFixedSize(20, 20)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"background:{color};color:white;border-radius:10px;font-weight:bold;")
    return lbl


def _section(title_label, number):
    """Numbered framed block → (frame, inner layout)."""
    frame = QFrame()
    frame.setObjectName("sec")
    frame.setStyleSheet("#sec{border:1px solid #c9c9c9;border-radius:4px;}")
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 6, 8, 8)
    box.setSpacing(5)
    head = QHBoxLayout()
    head.setSpacing(6)
    head.addWidget(_badge_label(str(number)))
    title_label.setStyleSheet("font-weight:bold;")
    head.addWidget(title_label)
    box.addLayout(head)
    return frame, box, head

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
                  "SQLite ou DXF, avec reprojection au choix et export limité à une zone : écran, "
                  "polygone ou rectangle dessiné, entités sélectionnées ou tampon.",
            'en': "Export Layers exports all the checked vector layers of the project in one go: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite or DXF, with optional reprojection and export limited to an area: map view, "
                  "drawn polygon or rectangle, selected features or buffer.",
            'es': "Export Layers exporta de una vez las capas vectoriales marcadas del proyecto: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite o DXF, con reproyección opcional y exportación limitada a una zona: vista, "
                  "polígono o rectángulo dibujado, entidades seleccionadas o búfer.",
            'pt': "O Export Layers exporta de uma só vez as camadas vetoriais marcadas do projeto: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite ou DXF, com reprojeção opcional e exportação limitada a uma zona: vista, "
                  "polígono ou retângulo desenhado, elementos selecionados ou buffer.",
            'de': "Export Layers exportiert alle markierten Vektorlayer des Projekts auf einmal: "
                  "GeoJSON, Shapefile, GeoPackage, CSV, Excel, KML, GML, FlatGeobuf, MapInfo TAB, "
                  "SQLite oder DXF, mit optionaler Umprojektion und Export auf einen Bereich begrenzt: "
                  "Kartenausschnitt, gezeichnetes Polygon oder Rechteck, ausgewählte Objekte oder Puffer."},
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
        self.setMinimumWidth(860)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)
        columns = QHBoxLayout()
        columns.setSpacing(10)
        layout.addLayout(columns, 1)

        # ══ Left column: ① Couches ══════════════════════════════════════════
        self.lbl_layers = QLabel()
        sec1, box1, head1 = _section(self.lbl_layers, 1)
        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("background:#eef6fd;border:1px solid #9cc7ec;"
                                     "border-radius:8px;padding:0 6px;font-size:11px;")
        head1.addWidget(self.lbl_count)
        head1.addStretch()
        self.filter_edit = QLineEdit()
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        box1.addWidget(self.filter_edit)

        self.layer_list = QTreeWidget()
        self.layer_list.setHeaderHidden(True)
        self.layer_list.setIndentation(14)
        self.layer_list.setUniformRowHeights(True)
        self.layer_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layers = {}
        self._populate_layers(initial=True)
        self.select_visible()                      # default: layers shown on the map
        box1.addWidget(self.layer_list, 1)

        btn_sel_layout = QHBoxLayout()
        self.btn_all  = QPushButton()
        self.btn_none = QPushButton()
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        self.btn_visible = QPushButton()
        self.btn_visible.clicked.connect(self.select_visible)
        btn_sel_layout.addWidget(self.btn_all)
        btn_sel_layout.addWidget(self.btn_none)
        btn_sel_layout.addWidget(self.btn_visible, 1)
        box1.addLayout(btn_sel_layout)
        sec1.setFixedWidth(310)
        columns.addWidget(sec1)

        # ══ Right column ════════════════════════════════════════════════════
        right = QVBoxLayout()
        right.setSpacing(6)
        columns.addLayout(right, 1)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        self.combo_lang = QComboBox()
        for code in LANGS:
            self.combo_lang.addItem(f"{LANG_FLAGS[code]}  {LANG_LABELS[code]}")
        self.combo_lang.setFixedHeight(26)
        self.combo_lang.setMinimumWidth(130)
        self.combo_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        top_layout.addWidget(self.combo_lang)
        self.btn_about = QPushButton()
        self.btn_about.setFixedWidth(90)
        self.btn_about.setFixedHeight(26)
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
        right.addLayout(top_layout)

        # ── ② Zone d'export ─────────────────────────────────────────────────
        self.lbl_zone = QLabel()
        sec2, box2, _head2 = _section(self.lbl_zone, 2)
        self.zone_combo = QComboBox(self)          # state holder, not shown
        self.zone_combo.setVisible(False)
        for _ in ZONE_MODES:
            self.zone_combo.addItem("")
        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.zone_group = QButtonGroup(self)
        self.zone_group.setExclusive(True)
        self.zone_buttons = []
        for i, _mode in enumerate(ZONE_MODES):
            b = QToolButton()
            b.setCheckable(True)
            b.setAutoRaise(False)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setMinimumHeight(26)
            b.setStyleSheet("QToolButton{border:1px solid #adadad;padding:2px 6px;}"
                            "QToolButton:checked{background:#cce4f7;border:1px solid #0078d7;font-weight:bold;}")
            self.zone_group.addButton(b, i)
            self.zone_buttons.append(b)
            seg.addWidget(b)
        self.zone_group.buttonClicked.connect(
            lambda b: self.zone_combo.setCurrentIndex(self.zone_buttons.index(b)))
        box2.addLayout(seg)

        zone_row = QHBoxLayout()
        zone_row.setSpacing(6)
        self.btn_draw = QPushButton()
        self.btn_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_draw.clicked.connect(self.start_drawing)
        self.zone_layer_combo = QgsMapLayerComboBox()
        self.zone_layer_combo.setMinimumWidth(150)
        self.spin_buffer = QDoubleSpinBox()
        self.spin_buffer.setRange(0.0, 100000.0)
        self.spin_buffer.setDecimals(1)
        self.spin_buffer.setSingleStep(10.0)
        self.spin_buffer.setValue(50.0)
        self.spin_buffer.setSuffix(" m")
        self.spin_buffer.setFixedWidth(90)
        self.lbl_zone_info = QLabel()
        self.lbl_zone_info.setMinimumHeight(24)
        zone_row.addWidget(self.zone_layer_combo, 1)
        zone_row.addWidget(self.btn_draw)
        zone_row.addWidget(self.spin_buffer)
        zone_row.addWidget(self.lbl_zone_info, 1)
        box2.addLayout(zone_row)

        clip_row = QHBoxLayout()
        clip_row.setSpacing(12)
        self.rb_whole = QRadioButton()
        self.rb_clip  = QRadioButton()
        self.rb_whole.setChecked(True)
        self.grp_clip = QButtonGroup(self)
        self.grp_clip.addButton(self.rb_whole)
        self.grp_clip.addButton(self.rb_clip)
        self.grp_clip.buttonToggled.connect(lambda *a: self._update_recap())
        clip_row.addWidget(self.rb_whole)
        clip_row.addWidget(self.rb_clip)
        clip_row.addStretch()
        box2.addLayout(clip_row)
        right.addWidget(sec2)

        # ── ③ Format et fichiers ────────────────────────────────────────────
        self.lbl_files = QLabel()
        sec3, box3, _head3 = _section(self.lbl_files, 3)
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(5)
        self.lbl_format = QLabel()
        self.format_combo = QComboBox()
        for fmt in FORMATS:
            self.format_combo.addItem(fmt)
        self.lbl_gpkg_info = QLabel()           # kept for compatibility, summed up in the recap
        self.lbl_gpkg_info.setVisible(False)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.lbl_crs = QLabel()
        self.crs_combo = QComboBox()
        self.crs_combo.currentIndexChanged.connect(lambda *a: self._update_recap())
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(6)
        fmt_row.addWidget(self.format_combo, 1)
        fmt_row.addWidget(self.lbl_crs)
        fmt_row.addWidget(self.crs_combo, 1)
        grid.addWidget(self.lbl_format, 0, 0)
        grid.addLayout(fmt_row, 0, 1)

        self.lbl_output = QLabel()
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(6)
        self.dir_edit   = QLineEdit()
        self.dir_edit.textChanged.connect(lambda *a: self._update_recap())
        self.btn_browse = QPushButton("📁")
        self.btn_browse.setFixedWidth(34)
        self.btn_browse.clicked.connect(self.browse_dir)
        self.btn_mkdir  = QPushButton()
        self.btn_mkdir.clicked.connect(self.create_folder)
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(self.btn_browse)
        dir_layout.addWidget(self.btn_mkdir)
        grid.addWidget(self.lbl_output, 1, 0)
        grid.addLayout(dir_layout, 1, 1)

        self.lbl_prefix   = QLabel()
        self.prefix_combo = QComboBox()
        for _ in PREFIX_MODES:
            self.prefix_combo.addItem("")
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setMaxLength(60)
        self.prefix_edit.setFixedWidth(90)
        self.lbl_prefix_example = QLabel()
        self.lbl_prefix_example.setStyleSheet("color: #1a6b3a; font-style: italic;")
        prefix_row = QHBoxLayout()
        prefix_row.setSpacing(6)
        prefix_row.addWidget(self.prefix_combo)
        prefix_row.addWidget(self.prefix_edit)
        prefix_row.addWidget(self.lbl_prefix_example, 1)
        grid.addWidget(self.lbl_prefix, 2, 0)
        grid.addLayout(prefix_row, 2, 1)
        grid.setColumnStretch(1, 1)
        box3.addLayout(grid)
        right.addWidget(sec3)

        settings = QgsSettings()
        mode = settings.value(SETTINGS_KEY + "prefix_mode", "none")
        self.prefix_combo.setCurrentIndex(PREFIX_MODES.index(mode) if mode in PREFIX_MODES else 0)
        self.prefix_edit.setText(settings.value(SETTINGS_KEY + "prefix_text", ""))
        self.prefix_combo.currentIndexChanged.connect(self._on_prefix_changed)
        self.prefix_edit.textChanged.connect(self._on_prefix_changed)
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)

        # ── ④ Style, mis en valeur ──────────────────────────────────────────
        self.chk_style = ToggleSwitch()
        self.chk_style.setChecked(QgsSettings().value(SETTINGS_KEY + "keep_style", False, type=bool))
        self.style_card = StyleCard(self.chk_style)
        card = QHBoxLayout(self.style_card)
        card.setContentsMargins(10, 5, 10, 5)
        card.setSpacing(10)
        card.addWidget(self.chk_style)
        palette = QLabel("🎨")
        palette.setStyleSheet("font-size:20px;")
        card.addWidget(palette)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        style_head = QHBoxLayout()
        style_head.setSpacing(8)
        self.style_badge = _badge_label("4")
        style_head.addWidget(self.style_badge)
        self.lbl_style_title = QLabel()
        self.lbl_style_title.setStyleSheet("font-weight:bold;font-size:13px;")
        style_head.addWidget(self.lbl_style_title)
        self.lbl_style_chip = QLabel()
        style_head.addWidget(self.lbl_style_chip)
        style_head.addStretch()
        texts.addLayout(style_head)
        self.lbl_style_msg = QLabel()
        self.lbl_style_msg.setWordWrap(True)
        self.lbl_style_msg.setStyleSheet("font-size:11px;")
        texts.addWidget(self.lbl_style_msg)
        card.addLayout(texts, 1)
        self.chk_style.toggled.connect(self._on_style_toggled)
        right.addWidget(self.style_card)

        # ── ⑤ Ajouter les couches au projet ─────────────────────────────────
        self.chk_add = ToggleSwitch()
        self.chk_add.setChecked(QgsSettings().value(SETTINGS_KEY + "add_to_project", False, type=bool))
        self.add_card = StyleCard(self.chk_add)
        add_box = QHBoxLayout(self.add_card)
        add_box.setContentsMargins(10, 4, 10, 4)
        add_box.setSpacing(10)
        add_box.addWidget(self.chk_add)
        plus = QLabel("➕")
        plus.setStyleSheet("font-size:18px;")
        add_box.addWidget(plus)
        add_texts = QVBoxLayout()
        add_texts.setSpacing(2)
        add_head = QHBoxLayout()
        add_head.setSpacing(8)
        self.add_badge = _badge_label("5")
        add_head.addWidget(self.add_badge)
        self.lbl_add_title = QLabel()
        self.lbl_add_title.setStyleSheet("font-weight:bold;font-size:13px;")
        add_head.addWidget(self.lbl_add_title)
        self.lbl_add_chip = QLabel()
        add_head.addWidget(self.lbl_add_chip)
        add_head.addStretch()
        add_texts.addLayout(add_head)
        self.lbl_add_msg = QLabel()
        self.lbl_add_msg.setWordWrap(True)
        self.lbl_add_msg.setStyleSheet("font-size:11px;")
        add_texts.addWidget(self.lbl_add_msg)
        add_box.addLayout(add_texts, 1)
        self.chk_add.toggled.connect(self._on_add_toggled)
        right.addWidget(self.add_card)

        # ── ⑥ Rassembler dans un ZIP ────────────────────────────────────────
        (self.zip_card, self.chk_zip, self.zip_badge, self.lbl_zip_title,
         self.lbl_zip_chip, self.lbl_zip_msg) = self._option_card(6, "🗜")
        self.chk_zip.setChecked(QgsSettings().value(SETTINGS_KEY + "zip", False, type=bool))
        self.chk_zip.toggled.connect(self._on_zip_toggled)
        right.addWidget(self.zip_card)

        right.addStretch()

        # ── Récapitulatif, progression, boutons ─────────────────────────────
        self.lbl_recap = QLabel()
        self.lbl_recap.setWordWrap(True)
        self.lbl_recap.setObjectName("recap")
        self.lbl_recap.setStyleSheet("#recap{border:1px solid #c9c9c9;border-radius:3px;padding:5px 8px;}")
        right.addWidget(self.lbl_recap)

        self.progress_status = QLabel()
        right.addWidget(self.progress_status)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        bottom.addWidget(self.progress_bar, 1)
        self.btn_log = QPushButton()
        self.btn_log.setCheckable(True)
        self.btn_log.toggled.connect(self._show_log)
        bottom.addWidget(self.btn_log)
        self.buttons    = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_export = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_close  = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.btn_export.setStyleSheet("QPushButton{background:#1a6b3a;color:white;font-weight:bold;"
                                      "padding:4px 16px;border-radius:3px;}"
                                      "QPushButton:disabled{background:#9bb8a6;}")
        self.buttons.accepted.connect(self.run_export)
        self.buttons.rejected.connect(self.reject)
        bottom.addWidget(self.buttons)
        right.addLayout(bottom)

        # ── Journal (replié par défaut, pleine largeur) ─────────────────────
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(96)
        self.log_area.setVisible(False)
        layout.addWidget(self.log_area)

        self._drawn_zones   = {}      # mode → (QgsGeometry, QgsCoordinateReferenceSystem)
        self._zone_rb       = None    # preview of the current zone on the canvas
        self._draw_tool     = None
        self._prev_tool     = None
        self._hint_item     = None
        self._watched_layer = None
        self._closed        = False
        self._selecting     = False   # dialog hidden while selecting on the map
        self._sel_prev_tool = None
        self._sel_prev_layer = None
        self._zone_area_text = ""
        self._zone_timer = QTimer(self)
        self._zone_timer.setSingleShot(True)
        self._zone_timer.setInterval(300)
        self._zone_timer.timeout.connect(self._refresh_zone_info)
        self.zone_combo.currentIndexChanged.connect(self._on_zone_mode_changed)
        self.zone_layer_combo.layerChanged.connect(self._on_zone_layer_changed)
        self.spin_buffer.valueChanged.connect(self._schedule_zone_refresh)

        self.setLayout(layout)
        self.apply_language()
        self._on_zone_mode_changed()
        self.resize(880, max(540, self.sizeHint().height()))

        project = QgsProject.instance()
        project.layersAdded.connect(self._on_project_layers_changed)
        project.layersRemoved.connect(self._on_project_layers_changed)
        _iface().mapCanvas().extentsChanged.connect(self._on_canvas_extent)

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
        self.lbl_layers.setText(self.t('sec_layers'))
        self.filter_edit.setPlaceholderText(self.t('filter_ph'))
        self.btn_all.setText(self.t('select_all_short'))
        self.btn_all.setToolTip(self.t('select_all'))
        self.btn_none.setText(self.t('select_none_short'))
        self.btn_none.setToolTip(self.t('select_none'))
        self.lbl_files.setText(self.t('sec_files'))
        self.lbl_format.setText(self.t('lbl_fmt'))
        self.lbl_crs.setText(self.t('lbl_crs'))
        self.lbl_output.setText(self.t('lbl_dir'))
        self.btn_browse.setToolTip(self.t('browse_tip'))
        self.btn_log.setText(self.t('log_btn') + "  ▸")
        for i, mode in enumerate(ZONE_MODES):
            self.zone_buttons[i].setText(self.t('zs_' + mode))
            self.zone_buttons[i].setToolTip(self.t('zone_' + mode))
        self.progress_status.setText(self.t('waiting'))
        self.progress_bar.setFormat(self.t('progress_format'))
        self.btn_visible.setText(self.t('select_visible'))
        self.btn_visible.setToolTip(self.t('select_visible_tip'))
        self.lbl_zone.setText(self.t('sec_zone'))
        for i, mode in enumerate(ZONE_MODES):
            self.zone_combo.setItemText(i, self.t('zone_' + mode))
        self._update_zone_button()
        self.zone_layer_combo.setToolTip(self.t('zone_layer_tip'))
        self.spin_buffer.setToolTip(self.t('buffer_tip'))
        self.rb_whole.setText(self.t('zone_whole'))
        self.rb_whole.setToolTip(self.t('zone_whole_tip'))
        self.rb_clip.setText(self.t('zone_clip'))
        self.rb_clip.setToolTip(self.t('zone_clip_tip'))
        self._refresh_zone_info()
        self.btn_export.setText(self.t('export_btn'))
        self.btn_close.setText(self.t('close_btn'))
        self.btn_about.setText(self.t('about_btn'))
        self.btn_mkdir.setText(self.t('mkdir_btn'))
        self.lbl_gpkg_info.setText(self.t('gpkg_info'))
        self.lbl_prefix.setText(self.t('lbl_prefix_short'))
        self.lbl_style_title.setText(self.t('keep_style'))
        self.lbl_add_title.setText(self.t('add_project'))
        self.lbl_zip_title.setText(self.t('zip_title'))
        self.style_card.setToolTip(self.t('keep_style_tip'))
        self._refresh_prefix_labels()
        self.prefix_combo.setToolTip(self.t('prefix_tip'))
        self.prefix_edit.setPlaceholderText(self.t('prefix_placeholder'))
        self._on_prefix_changed()
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
        self._update_count()
        self._update_style_card()
        self._update_add_card()
        self._update_zip_card()
        self._update_recap()

    def show_about(self):
        AboutDialog(lang=self.lang, parent=self).exec()

    def _on_format_changed(self, index):
        fmt = FORMATS.get(self.format_combo.currentText(), "")
        if hasattr(self, 'style_card'):
            self.chk_style.setEnabled(fmt in STYLE_FORMATS and self.format_combo.isEnabled())
            self._update_style_card()
        if hasattr(self, 'lbl_prefix_example'):
            self._update_prefix_example()
        if hasattr(self, 'lbl_recap'):
            self._update_recap()

    # ── Helper methods ────────────────────────────────────────────────────────

    def select_all(self):
        """Check every layer still shown by the filter."""
        for item in self._layer_items():
            if not item.isHidden():
                item.setCheckState(0, Qt.CheckState.Checked)

    def select_none(self):
        for item in self._layer_items():
            if not item.isHidden():
                item.setCheckState(0, Qt.CheckState.Unchecked)

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

    # ── Layer style ───────────────────────────────────────────────────────────

    def _save_style(self, src_layer, fmt, output_path, layer_name):
        """Keep the source layer style: inside the GeoPackage (default style) or as
        a .qml sidecar that QGIS loads automatically. Never fails the export."""
        try:
            if fmt == "gpkg":
                out = QgsVectorLayer(f"{output_path}|layername={layer_name}", layer_name, "ogr")
                if not out.isValid():
                    raise Exception(layer_name)
                style = QgsMapLayerStyle()
                style.readFromLayer(src_layer)
                style.writeToLayer(out)
                if hasattr(out, 'saveStyleToDatabaseV2'):
                    res = out.saveStyleToDatabaseV2(layer_name, "Export Couches Vecteur", True, "")
                    msg = res[-1] if isinstance(res, tuple) else ""
                else:
                    msg = out.saveStyleToDatabase(layer_name, "Export Couches Vecteur", True, "")
                del out                       # release the GeoPackage before the next layer
                if msg:
                    raise Exception(msg)
                self.log(self.t('style_saved_gpkg'))
            else:
                qml_path = os.path.splitext(output_path)[0] + ".qml"
                msg, ok = src_layer.saveNamedStyle(qml_path)
                if not ok:
                    raise Exception(msg)
                self.log(self.t('style_saved_qml', name=os.path.basename(qml_path)))
        except Exception as e:
            self.log(self.t('style_error', error=e))

    # ── Style card, recap ─────────────────────────────────────────────────────

    def _on_style_toggled(self, on):
        QgsSettings().setValue(SETTINGS_KEY + "keep_style", on)
        self._update_style_card()
        self._update_recap()

    def _option_card(self, number, icon):
        """Framed on/off block (switch, icon, numbered title, chip, explanation)."""
        switch = ToggleSwitch()
        card = StyleCard(switch)
        box = QHBoxLayout(card)
        box.setContentsMargins(10, 4, 10, 4)
        box.setSpacing(10)
        box.addWidget(switch)
        ic = QLabel(icon)
        ic.setStyleSheet("font-size:18px;")
        box.addWidget(ic)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        head = QHBoxLayout()
        head.setSpacing(8)
        badge = _badge_label(str(number))
        head.addWidget(badge)
        title = QLabel()
        title.setStyleSheet("font-weight:bold;font-size:13px;")
        head.addWidget(title)
        chip = QLabel()
        head.addWidget(chip)
        head.addStretch()
        texts.addLayout(head)
        msg = QLabel()
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size:11px;")
        texts.addWidget(msg)
        box.addLayout(texts, 1)
        return card, switch, badge, title, chip, msg

    def _paint_option_card(self, card, badge, chip, on):
        card.set_state('on' if on else 'off')
        badge.setStyleSheet("color:white;border-radius:10px;font-weight:bold;background:"
                            + ("#1a6b3a" if on else "#9aa5ad") + ";")
        chip.setText(self.t('style_on') if on else self.t('style_off'))
        chip.setStyleSheet("font-size:10px;font-weight:bold;color:white;border-radius:8px;"
                           "padding:1px 7px;background:" + ("#2e8b57" if on else "#9aa5ad") + ";")

    def _on_zip_toggled(self, on):
        QgsSettings().setValue(SETTINGS_KEY + "zip", on)
        self._update_zip_card()
        self._update_recap()

    def _zip_name(self, prefix=None):
        """<prefix><project>.zip, with date and time when the prefix has none."""
        if prefix is None:
            prefix = self._file_prefix() or ""
        project = sanitize_filename(QgsProject.instance().baseName() or "export")
        stamp = "" if re.match(r"\d{8}_", prefix) else "_" + datetime.now().strftime(DATETIME_FMT)
        return f"{prefix}{project}{stamp}.zip"

    def _update_zip_card(self):
        on = self.chk_zip.isChecked()
        self._paint_option_card(self.zip_card, self.zip_badge, self.lbl_zip_chip, on)
        if not on:
            self.lbl_zip_msg.setText(self.t('zip_off'))
        else:
            key = 'zip_on_keep' if self.chk_add.isChecked() else 'zip_on'
            self.lbl_zip_msg.setText(self.t(key, name=self._zip_name()))

    def _files_of_export(self):
        """Every file written by this export (shapefile parts and .qml included)."""
        files = []
        for uri, _name in self._exported:
            path = uri.split('|', 1)[0]
            stem = os.path.splitext(path)[0]
            for f in glob.glob(glob.escape(stem) + ".*"):
                if f.lower().endswith(".zip") or f in files:
                    continue
                if os.path.getmtime(f) >= self._export_t0 - 2:     # only this export
                    files.append(f)
        return files

    def _zip_exported(self, output_dir, prefix):
        """Gather the files of this export into one ZIP; delete them unless the
        layers were added to the project (they read the files)."""
        if not self.chk_zip.isChecked() or not self._exported:
            return
        files = self._files_of_export()
        if not files:
            return
        name = self._zip_name(prefix)
        zip_path, n = os.path.join(output_dir, name), 2
        while os.path.exists(zip_path):
            zip_path, n = os.path.join(output_dir, f"{os.path.splitext(name)[0]} ({n}).zip"), n + 1
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, os.path.basename(f))
        except (OSError, zipfile.BadZipFile) as e:
            self.log(self.t('zip_error', error=e))
            return
        if not self.chk_add.isChecked():
            for f in files:
                try:
                    os.remove(f)
                except OSError:
                    pass
        self.log(self.t('zip_log', n=len(files), name=os.path.basename(zip_path)))

    def _on_add_toggled(self, on):
        QgsSettings().setValue(SETTINGS_KEY + "add_to_project", on)
        self._update_add_card()
        if hasattr(self, 'chk_zip'):
            self._update_zip_card()
        self._update_recap()

    def _update_add_card(self):
        on = self.chk_add.isChecked()
        self.add_card.set_state('on' if on else 'off')
        self.add_badge.setStyleSheet("color:white;border-radius:10px;font-weight:bold;background:"
                                     + ("#1a6b3a" if on else "#9aa5ad") + ";")
        self.lbl_add_chip.setText(self.t('style_on') if on else self.t('style_off'))
        self.lbl_add_chip.setStyleSheet("font-size:10px;font-weight:bold;color:white;border-radius:8px;"
                                        "padding:1px 7px;background:" + ("#2e8b57" if on else "#9aa5ad") + ";")
        self.lbl_add_msg.setText(self.t('add_project_on', date=datetime.now().strftime(DATETIME_FMT))
                                 if on else self.t('add_project_off'))

    def _add_exported_to_project(self):
        """Open the files written by this export in a new group at the top of the tree."""
        if not self.chk_add.isChecked() or not self._exported:
            return
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        base_name = self.t('added_group', date=datetime.now().strftime(DATETIME_FMT))
        group_name, n = base_name, 2
        while root.findGroup(group_name) is not None:      # two exports in the same minute
            group_name, n = f"{base_name} ({n})", n + 1
        group = root.insertGroup(0, group_name)
        added = 0
        for uri, name in self._exported:
            layer = QgsVectorLayer(uri, name, "ogr")
            if not layer.isValid():
                self.log(self.t('added_fail', name=name))
                continue
            project.addMapLayer(layer, False)
            group.addLayer(layer)
            added += 1
        if added == 0:
            project.layerTreeRoot().removeChildNode(group)
            return
        self.log(self.t('added_log', n=added, group=group_name))

    def _style_kept(self):
        fmt = FORMATS.get(self.format_combo.currentText(), "")
        return fmt in (DXF_FORMAT, DXF_SINGLE_FORMAT) or \
            (fmt in STYLE_FORMATS and self.chk_style.isChecked())

    def _update_style_card(self):
        fmt = FORMATS.get(self.format_combo.currentText(), "")
        chip_css = "font-size:10px;font-weight:bold;color:white;border-radius:8px;padding:1px 7px;background:{};"
        if fmt in (DXF_FORMAT, DXF_SINGLE_FORMAT):
            state, chip, msg, color = 'on', 'style_always', 'style_msg_dxf', "#2e8b57"
        elif fmt not in STYLE_FORMATS:
            state, chip, msg, color = 'na', 'style_na', 'style_msg_na', "#9aa5ad"
        elif self.chk_style.isChecked():
            state, chip, color = 'on', 'style_on', "#2e8b57"
            msg = 'style_msg_gpkg' if fmt == "gpkg" else 'style_msg_qml'
        else:
            state, chip, msg, color = 'off', 'style_off', 'style_msg_off', "#9aa5ad"
        self.chk_style.forced_on = fmt in (DXF_FORMAT, DXF_SINGLE_FORMAT)
        self.chk_style.unavailable = state == 'na'
        self.chk_style.update()
        self.style_card.set_state(state)
        self.style_card.setCursor(Qt.CursorShape.PointingHandCursor if fmt in STYLE_FORMATS
                                  else Qt.CursorShape.ArrowCursor)
        self.style_badge.setStyleSheet("color:white;border-radius:10px;font-weight:bold;background:"
                                       + ("#1a6b3a" if state == 'on' else "#9aa5ad") + ";")
        self.lbl_style_chip.setText(self.t(chip))
        self.lbl_style_chip.setStyleSheet(chip_css.format(color))
        self.lbl_style_msg.setText(self.t(msg))

    def _update_recap(self, *args):
        if not hasattr(self, 'lbl_recap') or not hasattr(self, '_zone_area_text'):
            return
        n   = sum(1 for it in self._layer_items() if it.checkState(0) == Qt.CheckState.Checked)
        fmt = FORMATS.get(self.format_combo.currentText(), "")
        ext = {"dxf_single": "DXF", "gpkg": "GeoPackage"}.get(fmt, fmt.upper())
        target = (self.t('recap_one_file', ext=ext) if fmt in ("gpkg", "dxf_single")
                  else self.t('recap_files', n=n, ext=ext))
        mode = self._zone_mode()
        if mode == 'all':
            zone = self.t('zone_all')
        else:
            zone = self.t('zs_' + mode).split(' ', 1)[-1]
            if self._zone_area_text:
                zone += f" ({self._zone_area_text})"
            clip_txt = (self.rb_clip.text() if self.rb_clip.isChecked()
                        else self.rb_whole.text())
            zone += ", " + (clip_txt if self.lang == 'de' else clip_txt.lower())
        parts = [f"<b>{self.t('recap_layers', n=n)}</b> → {target}",
                 f"<b>{zone}</b>", self.crs_combo.currentText().split(' — ')[0]]
        prefix = self._file_prefix() if hasattr(self, 'prefix_combo') else ""
        if prefix:
            parts.append(prefix)
        if self._style_kept():
            parts.append(f"<b style='color:#1a6b3a'>{self.t('recap_style')}</b>")
        if getattr(self, 'chk_add', None) is not None and self.chk_add.isChecked():
            parts.append(f"<b style='color:#1a6b3a'>{self.t('recap_added')}</b>")
        if getattr(self, 'chk_zip', None) is not None and self.chk_zip.isChecked():
            parts.append(f"<b style='color:#1a6b3a'>{self.t('recap_zip')}</b>")
        self.lbl_recap.setText("▶ " + " · ".join(parts))

    # ── File name prefix ──────────────────────────────────────────────────────

    def _refresh_prefix_labels(self):
        """Combo texts show today's date / the current time."""
        now = datetime.now()
        for i, mode in enumerate(PREFIX_MODES):
            if mode == 'date':
                text = self.t('prefix_date', date=now.strftime(DATE_FMT))
            elif mode == 'datetime':
                text = self.t('prefix_datetime', date=now.strftime(DATETIME_FMT))
            else:
                text = self.t('prefix_' + mode)
            if self.prefix_combo.itemText(i) != text:
                self.prefix_combo.setItemText(i, text)

    def _file_prefix(self):
        """'20261113_', '20261113_1154_', 'TEXT_', '20261113_TEXT_' or '';
        None if the text is missing."""
        mode  = PREFIX_MODES[max(self.prefix_combo.currentIndex(), 0)]
        now   = datetime.now()
        parts = []
        if mode in ('date', 'date_text'):
            parts.append(now.strftime(DATE_FMT))
        elif mode == 'datetime':
            parts.append(now.strftime(DATETIME_FMT))
        if 'text' in mode:
            text = sanitize_filename(self.prefix_edit.text().strip()).strip()
            if not text:
                return None
            parts.append(text)
        return "_".join(parts) + "_" if parts else ""

    def _on_prefix_changed(self, *args):
        mode = PREFIX_MODES[max(self.prefix_combo.currentIndex(), 0)]
        self.prefix_edit.setVisible('text' in mode)
        self.prefix_edit.setEnabled(self.prefix_combo.isEnabled())
        settings = QgsSettings()
        settings.setValue(SETTINGS_KEY + "prefix_mode", mode)
        settings.setValue(SETTINGS_KEY + "prefix_text", self.prefix_edit.text())
        self._update_prefix_example()
        if hasattr(self, 'chk_zip'):
            self._update_zip_card()
        self._update_recap()

    def _update_prefix_example(self, *args):
        self._refresh_prefix_labels()
        prefix = self._file_prefix()
        if not prefix:
            self.lbl_prefix_example.setText("")
            return
        layers = self.get_selected_layers()
        name = sanitize_filename(layers[0].name()) if layers else self.t('example_layer')
        fmt  = FORMATS.get(self.format_combo.currentText(), "")
        ext  = {"dxf_single": "dxf"}.get(fmt, fmt)
        if fmt in ("gpkg", "dxf_single"):
            name = sanitize_filename(QgsProject.instance().baseName() or "export")
        self.lbl_prefix_example.setText(self.t('prefix_example', name=f"{prefix}{name}.{ext}"))

    def _ask_gpkg_path(self, output_dir, prefix=""):
        """Ask the GeoPackage file name; return its full path or None if cancelled."""
        default = prefix + sanitize_filename(QgsProject.instance().baseName() or "export")
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
        """Checked layers, in map rendering order (top → bottom)."""
        project = QgsProject.instance()
        checked = {item.data(0, LAYER_ID_ROLE) for item in self._layer_items()
                   if item.checkState(0) == Qt.CheckState.Checked}
        return [layer for layer in self._ordered_vector_layers() if layer.id() in checked
                and project.mapLayer(layer.id()) is not None]

    def log(self, message):
        self.log_area.append(message)
        QApplication.processEvents()

    def _warn(self, message):
        """Blocking problem before export: shown on the status line, not only in the log."""
        self.log_area.append(message)
        self.progress_status.setStyleSheet("color:#c0392b;font-weight:bold;")
        self.progress_status.setText(message.strip())

    def _show_log(self, show):
        if self.btn_log.isChecked() != show:
            self.btn_log.setChecked(show)       # re-enters with the same value
            return
        if self.log_area.isVisible() == show:
            return
        before = self.height()                      # Qt may grow the window by itself
        self.log_area.setVisible(show)
        self.btn_log.setText(self.t('log_btn') + ("  ▾" if show else "  ▸"))
        target = before + (102 if show else -102)
        screen = self.screen().availableGeometry().height() if hasattr(self, 'screen') else 10000
        QTimer.singleShot(0, lambda: self.resize(
            self.width(), min(max(self.minimumSizeHint().height(), target), screen - 40)))

    def set_controls_enabled(self, enabled):
        self.layer_list.setEnabled(enabled)
        self.filter_edit.setEnabled(enabled)
        for b in self.zone_buttons:
            b.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.crs_combo.setEnabled(enabled)
        self.dir_edit.setEnabled(enabled)
        self.prefix_combo.setEnabled(enabled)
        self.chk_add.setEnabled(enabled)
        self.chk_zip.setEnabled(enabled)
        self.chk_style.setEnabled(enabled and
                                  FORMATS.get(self.format_combo.currentText(), "") in STYLE_FORMATS)
        self.prefix_edit.setEnabled(enabled and 'text' in PREFIX_MODES[self.prefix_combo.currentIndex()])
        for w in (self.btn_all, self.btn_none, self.btn_visible,
                  self.zone_combo, self.btn_draw, self.zone_layer_combo,
                  self.spin_buffer, self.rb_whole, self.rb_clip):
            w.setEnabled(enabled)
        if enabled:
            self.rb_whole.setEnabled(self._zone_mode() != 'all')
            self.rb_clip.setEnabled(self._zone_mode() != 'all')
        self.btn_export.setEnabled(enabled)
        self.combo_lang.setEnabled(enabled)

    # ── Layer list: tree order, quick selections ─────────────────────────────

    def _ordered_vector_layers(self):
        """Vector layers in map rendering order (top → bottom), then the others."""
        project = QgsProject.instance()
        seen, out = set(), []
        for layer in project.layerTreeRoot().layerOrder() + list(project.mapLayers().values()):
            if isinstance(layer, QgsVectorLayer) and layer.id() not in seen:
                seen.add(layer.id())
                out.append(layer)
        return out

    def _layer_items(self):
        """Every layer (leaf) item of the tree."""
        out, stack = [], [self.layer_list.topLevelItem(i)
                          for i in range(self.layer_list.topLevelItemCount())]
        while stack:
            item = stack.pop(0)
            if item.data(0, LAYER_ID_ROLE):
                out.append(item)
            stack[0:0] = [item.child(i) for i in range(item.childCount())]
        return out

    def _populate_layers(self, initial=False):
        """(Re)build the tree with the Layers panel groups; keep check states,
        new layers come unchecked."""
        previous = {item.data(0, LAYER_ID_ROLE): item.checkState(0) for item in self._layer_items()}
        default = Qt.CheckState.Checked if initial else Qt.CheckState.Unchecked
        tree = self.layer_list
        tree.blockSignals(True)
        tree.clear()
        self.layers = {}
        project = QgsProject.instance()
        vector_ids = {l.id() for l in self._ordered_vector_layers()}
        placed = set()

        def make_layer_item(parent, layer):
            provider = layer.dataProvider()
            label = f"{layer.name()}  [{provider.name() if provider else '?'}]"
            item = QTreeWidgetItem(parent, [label])
            item.setData(0, LAYER_ID_ROLE, layer.id())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, previous.get(layer.id(), default))
            if QgsIconUtils is not None:
                item.setIcon(0, QgsIconUtils.iconForLayer(layer))
            self.layers[label] = layer
            placed.add(layer.id())

        def walk(node, parent):
            for child in node.children():
                if hasattr(child, 'layerId'):                     # layer node
                    layer = project.mapLayer(child.layerId())
                    if isinstance(layer, QgsVectorLayer) and layer.id() not in placed:
                        make_layer_item(parent, layer)
                else:                                             # group node
                    ids = [l.layerId() for l in child.findLayers()]
                    if not any(i in vector_ids for i in ids):
                        continue
                    group = QTreeWidgetItem(parent, [child.name()])
                    group.setFlags(group.flags() | Qt.ItemFlag.ItemIsUserCheckable
                                   | Qt.ItemFlag.ItemIsAutoTristate)
                    font = group.font(0)
                    font.setBold(True)
                    group.setFont(0, font)
                    walk(child, group)
                    group.setExpanded(child.isExpanded())

        walk(project.layerTreeRoot(), tree.invisibleRootItem())
        for layer in self._ordered_vector_layers():         # layers outside the tree
            if layer.id() not in placed:
                make_layer_item(tree.invisibleRootItem(), layer)
        tree.blockSignals(False)
        if hasattr(self, 'filter_edit'):
            self._apply_filter(self.filter_edit.text())
        if hasattr(self, 'lbl_count'):
            self._update_count()
            self._update_recap()

    def _apply_filter(self, text):
        """Hide layers whose name does not contain the text, and empty groups."""
        needle = (text or "").strip().lower()

        def visit(item):
            if item.data(0, LAYER_ID_ROLE):
                hidden = bool(needle) and needle not in item.text(0).lower()
                item.setHidden(hidden)
                return not hidden
            shown = False
            for i in range(item.childCount()):
                shown = visit(item.child(i)) or shown
            item.setHidden(not shown)
            if needle and shown:
                item.setExpanded(True)
            return shown

        for i in range(self.layer_list.topLevelItemCount()):
            visit(self.layer_list.topLevelItem(i))

    def _on_layer_item_changed(self, *args):
        self._update_count()
        self._update_prefix_example()
        self._update_recap()

    def _update_count(self):
        items = self._layer_items()
        n = sum(1 for it in items if it.checkState(0) == Qt.CheckState.Checked)
        self.lbl_count.setText(self.t('count_checked', n=n, total=len(items)))

    def _on_project_layers_changed(self, *args):
        if not self._closed:
            self._populate_layers()

    def _check_only(self, layer_ids):
        for item in self._layer_items():
            item.setCheckState(0, Qt.CheckState.Checked if item.data(0, LAYER_ID_ROLE) in layer_ids
                               else Qt.CheckState.Unchecked)

    def select_visible(self):
        """Check the layers drawn on the map canvas (visible and within scale range)."""
        canvas = _iface().mapCanvas()
        scale  = canvas.scale()
        ids = {layer.id() for layer in canvas.layers()
               if not layer.hasScaleBasedVisibility() or layer.isInScaleRange(scale)}
        self._check_only(ids)

    # ── Export zone ───────────────────────────────────────────────────────────

    def _update_zone_button(self):
        """One button: 'Draw' for drawn zones, 'Select' for selection-based zones."""
        mode = self._zone_mode()
        self.btn_draw.setVisible(mode in DRAWN_MODES or mode in SELECTION_MODES)
        if mode in SELECTION_MODES:
            self.btn_draw.setText(self.t('pick_btn'))
            self.btn_draw.setToolTip(self.t('pick_tip'))
        else:
            self.btn_draw.setText(self.t('draw_btn'))
            self.btn_draw.setToolTip("")

    def _zone_mode(self):
        return ZONE_MODES[max(self.zone_combo.currentIndex(), 0)]

    def _on_zone_mode_changed(self, *args):
        mode = self._zone_mode()
        idx = ZONE_MODES.index(mode)
        if not self.zone_buttons[idx].isChecked():
            self.zone_buttons[idx].setChecked(True)
        self._update_zone_button()
        self.zone_layer_combo.setVisible(mode in SELECTION_MODES)
        self.spin_buffer.setVisible(mode == 'buffer')
        self.rb_whole.setEnabled(mode != 'all' and self.zone_combo.isEnabled())
        self.rb_clip.setEnabled(mode != 'all' and self.zone_combo.isEnabled())
        if mode in SELECTION_MODES:
            wanted = 'PolygonLayer' if mode == 'selection' else 'HasGeometry'
            self.zone_layer_combo.setFilters(_layer_filter(wanted))
            # active layer first, then the first layer (map order) with a selection
            current = self.zone_layer_combo.currentLayer()
            if not (self._fits_zone_mode(current, mode) and current.selectedFeatureCount()):
                for cand in [_iface().activeLayer()] + self._ordered_vector_layers():
                    if self._fits_zone_mode(cand, mode) and cand.selectedFeatureCount():
                        self.zone_layer_combo.setLayer(cand)
                        break
            self._on_zone_layer_changed(self.zone_layer_combo.currentLayer())
        else:
            self._refresh_zone_info()

    @staticmethod
    def _fits_zone_mode(layer, mode):
        return (isinstance(layer, QgsVectorLayer) and layer.isSpatial()
                and (mode == 'buffer' or layer.geometryType() == POLYGON_TYPE))

    def _on_zone_layer_changed(self, layer=None):
        """Follow the selection of the zone source layer."""
        if self._watched_layer is not None:
            try:
                self._watched_layer.selectionChanged.disconnect(self._schedule_zone_refresh)
            except (TypeError, RuntimeError):
                pass
        self._watched_layer = layer if isinstance(layer, QgsVectorLayer) else None
        if self._watched_layer is not None:
            self._watched_layer.selectionChanged.connect(self._schedule_zone_refresh)
        self._schedule_zone_refresh()

    def _schedule_zone_refresh(self, *args):
        if not self._closed:
            self._zone_timer.start()

    def _on_canvas_extent(self):
        if self._zone_mode() == 'screen' and self.isVisible():
            self._schedule_zone_refresh()

    def _compute_zone(self):
        """Current zone as (geometry, crs, description, feature count or None).

        Returns None for 'whole layer'; raises ZoneError when the zone cannot be built.
        """
        mode = self._zone_mode()
        if mode == 'all':
            return None
        count = None
        if mode == 'screen':
            ms   = _iface().mapCanvas().mapSettings()
            pts  = [QgsPointXY(pt.x(), pt.y()) for pt in ms.visiblePolygon()]
            geom = QgsGeometry.fromPolygonXY([pts + [pts[0]]]) if len(pts) >= 3 else None
            crs  = ms.destinationCrs()
            desc = self.t('zone_screen')
        elif mode in DRAWN_MODES:
            if mode not in self._drawn_zones:
                raise ZoneError(self.t('zone_not_drawn'))
            geom, crs = self._drawn_zones[mode]
            geom = QgsGeometry(geom)
            desc = self.t('zone_' + mode)
        else:
            layer = self.zone_layer_combo.currentLayer()
            if not isinstance(layer, QgsVectorLayer) or not layer.isSpatial():
                raise ZoneError(self.t('zone_no_layer'))
            if mode == 'selection' and layer.geometryType() != POLYGON_TYPE:
                raise ZoneError(self.t('zone_not_polygon', layer=layer.name()))
            geoms = [f.geometry() for f in layer.getSelectedFeatures() if f.hasGeometry()]
            if not geoms:
                raise ZoneError(self.t('zone_no_selection', layer=layer.name()))
            count = len(geoms)
            crs   = layer.crs()
            geom  = QgsGeometry.unaryUnion(geoms)
            if geom is None or geom.isNull() or geom.isEmpty():   # invalid parts
                geom = QgsGeometry.unaryUnion([g.makeValid() for g in geoms])
            if mode == 'buffer':
                dist = self.spin_buffer.value()
                if dist <= 0:
                    raise ZoneError(self.t('zone_bad_distance'))
                work = metric_crs_for(geom, crs)     # never buffer in degrees
                geom = transform_geometry(geom, crs, work).buffer(dist, 12)
                crs  = work
                desc = f"{self.t('zone_buffer')} {self._fmt_num(dist, 1)} m « {layer.name()} »"
            else:
                desc = f"{self.t('zone_selection')} « {layer.name()} »"
        if geom is None or geom.isNull() or geom.isEmpty():
            raise ZoneError(self.t('zone_invalid'))
        if not geom.isGeosValid():
            geom = geom.makeValid()
        return geom, crs, desc, count

    def _fmt_num(self, value, decimals):
        text = f"{value:,.{decimals}f}"
        if self.lang == 'en':
            return text
        return text.replace(',', '\u00a0').replace('.', ',')

    def _fmt_area(self, m2):
        if m2 < 10000:
            return self._fmt_num(m2, 0) + " m²"
        if m2 < 1e8:
            return self._fmt_num(m2 / 1e4, 2) + " ha"
        return self._fmt_num(m2 / 1e6, 2) + " km²"

    def _refresh_zone_info(self):
        if self._closed:
            return
        mode = self._zone_mode()
        self._show_zone_preview(None)
        self._zone_area_text = ""
        if mode == 'all':
            self.lbl_zone_info.setStyleSheet("color: #555; font-style: italic;")
            self.lbl_zone_info.setText(self.t('zone_all_info'))
            self._update_recap()
            return
        try:
            geom, crs, _desc, count = self._compute_zone()
        except ZoneError as e:
            self.lbl_zone_info.setStyleSheet("color: #c0392b; font-style: italic;")
            self.lbl_zone_info.setText(str(e))
            self._update_recap()
            return
        area = self._fmt_area(zone_area_m2(geom, crs))
        self._zone_area_text = area
        QTimer.singleShot(0, self._update_recap)
        self.lbl_zone_info.setStyleSheet("color: #1a6b3a; font-style: italic;")
        self.lbl_zone_info.setText(self.t('zone_info_sel', n=count, area=area) if count
                                   else self.t('zone_info_area', area=area))
        if mode != 'screen':
            self._show_zone_preview(geom, crs)

    def _show_zone_preview(self, geom, crs=None):
        if geom is None:
            if self._zone_rb is not None:
                self._zone_rb.reset(POLYGON_TYPE)
            return
        if self._zone_rb is None:
            self._zone_rb = make_rubber_band(_iface().mapCanvas(), dashed=True)
        self._zone_rb.setToGeometry(geom, crs)

    # ── Drawing on the canvas ────────────────────────────────────────────────

    def start_drawing(self):
        mode = self._zone_mode()
        if mode in SELECTION_MODES:
            self._start_selecting()
            return
        if mode not in DRAWN_MODES or self._draw_tool is not None:
            return
        canvas = _iface().mapCanvas()
        self._prev_tool = canvas.mapTool()
        tool = ZoneMapTool(canvas, mode)
        tool.zoneDrawn.connect(self._on_zone_drawn)
        tool.canceled.connect(self._on_draw_canceled)
        self._draw_tool = tool          # keep a Python reference while it is set
        self._show_zone_preview(None)
        self._push_hint(self.t('hint_' + mode))
        self.hide()
        canvas.setMapTool(tool)
        canvas.setFocus()

    SELECT_ACTIONS = ('actionSelect', 'actionSelectRectangle', 'actionSelectPolygon',
                      'actionSelectFreehand', 'actionSelectRadius')

    def _start_selecting(self):
        """QGIS selects on the ACTIVE layer: make the zone layer active, start the
        select tool and hide the dialog until the user is done."""
        layer = self.zone_layer_combo.currentLayer()
        if not isinstance(layer, QgsVectorLayer) or self._selecting:
            return
        iface  = _iface()
        canvas = iface.mapCanvas()
        self._sel_prev_tool  = canvas.mapTool()
        self._sel_prev_layer = iface.activeLayer()
        iface.setActiveLayer(layer)
        iface.actionSelect().trigger()

        text = self.t('hint_select', layer=layer.name())
        if layer not in canvas.layers():
            text += self.t('hint_hidden')
        bar    = iface.messageBar()
        widget = bar.createMessage(self.t('zone_label').rstrip(' :'), text)
        btn_done = QPushButton(self.t('pick_done'))
        btn_done.clicked.connect(lambda: self._end_selecting(True))
        widget.layout().addWidget(btn_done)
        self._pop_hint()
        level = getattr(getattr(Qgis, 'MessageLevel', Qgis), 'Info')
        self._hint_item = bar.pushWidget(widget, level)

        self._selecting = True
        canvas.viewport().installEventFilter(self)
        canvas.installEventFilter(self)
        canvas.mapToolSet.connect(self._on_map_tool_set)
        self.hide()
        canvas.setFocus()

    def _end_selecting(self, restore=True):
        """Back to the dialog; restore the previous active layer and map tool."""
        if not self._selecting:
            return
        self._selecting = False
        iface  = _iface()
        canvas = iface.mapCanvas()
        canvas.viewport().removeEventFilter(self)
        canvas.removeEventFilter(self)
        try:
            canvas.mapToolSet.disconnect(self._on_map_tool_set)
        except (TypeError, RuntimeError):
            pass
        self._pop_hint()
        if restore:
            try:
                if self._sel_prev_layer is not None:
                    iface.setActiveLayer(self._sel_prev_layer)
                if self._sel_prev_tool is not None:
                    canvas.setMapTool(self._sel_prev_tool)
            except RuntimeError:            # layer or tool deleted meanwhile
                pass
        self._sel_prev_tool = self._sel_prev_layer = None
        if not self._closed:
            self.show()
            self.raise_()
            self.activateWindow()
            self._refresh_zone_info()

    def _on_map_tool_set(self, new_tool, old_tool=None):
        """Another (non-selection) tool picked: give the dialog back, keep that tool."""
        if not self._selecting:
            return
        iface = _iface()
        select_actions = [getattr(iface, name)() for name in self.SELECT_ACTIONS
                          if hasattr(iface, name)]
        action = new_tool.action() if new_tool is not None else None
        if action is not None and action in select_actions:
            return
        QTimer.singleShot(0, lambda: self._end_selecting(False))

    def eventFilter(self, obj, event):
        if self._selecting:
            etype = event.type()
            if etype == QEvent.Type.MouseButtonRelease and \
                    event.button() == Qt.MouseButton.RightButton:
                QTimer.singleShot(0, lambda: self._end_selecting(True))
                return True
            if etype == QEvent.Type.KeyPress and \
                    event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                QTimer.singleShot(0, lambda: self._end_selecting(True))
                return True
        return super().eventFilter(obj, event)

    def bring_back(self):
        """Plugin icon clicked while the dialog is hidden (drawing / selecting)."""
        if self._selecting:
            self._end_selecting(True)
            return
        if self._draw_tool is not None:
            self._release_draw_tool()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_zone_drawn(self, geom):
        canvas = _iface().mapCanvas()
        self._drawn_zones[self._draw_tool.mode] = (QgsGeometry(geom),
                                                   canvas.mapSettings().destinationCrs())
        QTimer.singleShot(0, self._finish_drawing)

    def _on_draw_canceled(self, _restore):
        # may come from the tool's deactivate(): finish outside of it
        QTimer.singleShot(0, self._finish_drawing)

    def _finish_drawing(self):
        self._release_draw_tool()
        if self._closed:
            return
        self.show()
        self.raise_()
        self.activateWindow()
        self._refresh_zone_info()

    def _release_draw_tool(self):
        tool, self._draw_tool = self._draw_tool, None
        self._pop_hint()
        if tool is None:
            return
        canvas = _iface().mapCanvas()
        if canvas.mapTool() is tool:      # finished or Esc: give the previous tool back
            try:
                if self._prev_tool is not None:
                    canvas.setMapTool(self._prev_tool)
                else:
                    canvas.unsetMapTool(tool)
            except RuntimeError:
                canvas.unsetMapTool(tool)
        self._prev_tool = None
        tool.cleanup()
        tool.deleteLater()

    def _push_hint(self, text):
        self._pop_hint()
        bar   = _iface().messageBar()
        level = getattr(getattr(Qgis, 'MessageLevel', Qgis), 'Info')
        self._hint_item = bar.pushWidget(
            bar.createMessage(self.t('zone_label').rstrip(' :'), text), level)

    def _pop_hint(self):
        if self._hint_item is not None:
            try:
                _iface().messageBar().popWidget(self._hint_item)
            except RuntimeError:
                pass
            self._hint_item = None

    def _apply_zone(self, layer, zone, clip):
        """Layer limited to the zone (memory copy), or the layer itself."""
        if zone is None:
            return layer
        if not layer.isSpatial():
            self.log(self.t('zone_skip_nogeom'))
            return layer
        mem, kept, _examined = filter_layer_by_zone(layer, zone[0], zone[1], clip)
        self.log(self.t('zone_count', kept=kept))
        return mem

    def done(self, result):
        """Close: remove the zone preview, the drawing tool and the signal links."""
        if not self._closed:
            self._closed = True
            self._zone_timer.stop()
            self._end_selecting(True)
            self._release_draw_tool()
            canvas = _iface().mapCanvas()
            remove_rubber_band(canvas, self._zone_rb)
            self._zone_rb = None
            self._on_zone_layer_changed(None)
            for signal, slot in ((QgsProject.instance().layersAdded, self._on_project_layers_changed),
                                 (QgsProject.instance().layersRemoved, self._on_project_layers_changed),
                                 (canvas.extentsChanged, self._on_canvas_extent)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        super().done(result)

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
            raise Exception(self.t('file_open_error', path=output_path))
        try:
            result = export.writeToFile(f, 'CP1252')
        finally:
            f.close()

        if result != QgsDxfExport.ExportResult.Success:
            raise Exception(f"QgsDxfExport : {result}")

    def export_dxf(self, layer, output_path, crs_code):
        """Export DXF d'une couche unique (appelé par la boucle principale)."""
        has_labels = layer.labelsEnabled() and layer.labeling()
        self.log(self.t('dxf_labels_yes') if has_labels else self.t('dxf_labels_no'))
        self._dxf_write([layer], output_path, crs_code)

    # ── DXF single-file export ────────────────────────────────────────────────

    def _run_export_dxf_single(self, layers, output_dir, crs_code, zone=None, prefix=""):
        project_name = QgsProject.instance().baseName() or "export"
        output_path  = os.path.join(output_dir, prefix + sanitize_filename(project_name) + ".dxf")

        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)
        self.log(self.t('export_start', total=len(layers)))

        # kept_alive : empêche Python de GC les couches mémoire pendant l'export
        kept_alive = []
        export_layers = []
        for layer in reversed(layers):   # bottom→top = ordre d'écriture DXF
            has_labels = layer.labelsEnabled() and layer.labeling()
            self.log(f"  + {layer.name()}" + (self.t('dxf_labels_tag') if has_labels else ""))
            lyr = self._apply_zone(layer, zone, self.rb_clip.isChecked())
            if lyr is not layer:
                kept_alive.append(lyr)
            export_layers.append(lyr)

        try:
            self._dxf_write(export_layers, output_path, crs_code)
            self.log(self.t('export_ok', path=output_path))
            self._exported.append((output_path, os.path.splitext(os.path.basename(output_path))[0]))
            self.progress_status.setText(self.t('export_done_ok', total=len(layers)))
        except Exception as e:
            self.log(self.t('export_error', error=e))
            self.progress_status.setText(self.t('export_done_error', errors=1, total=1))
            self._show_log(True)
        finally:
            kept_alive.clear()

        self.progress_bar.setValue(1)
        self._add_exported_to_project()
        self._zip_exported(output_dir, prefix)
        self.log(self.t('export_end'))
        self.set_controls_enabled(True)

    # ── Main export orchestration ─────────────────────────────────────────────

    def run_export(self):
        selected_layers = self.get_selected_layers()
        fmt        = FORMATS[self.format_combo.currentText()]
        output_dir = self.dir_edit.text().strip()
        crs_code   = self._crs_values[self.crs_combo.currentIndex()]

        if not selected_layers:
            self._warn(self.t('no_layer'))
            return
        if not output_dir:
            self._warn(self.t('no_dir'))
            return

        prefix = self._file_prefix()
        if prefix is None:
            self._warn(self.t('prefix_empty'))
            return

        # ── Zone d'export : calculée une fois, avant toute écriture ───────
        try:
            zone = self._compute_zone()
        except ZoneError as e:
            self._warn(self.t('zone_error', error=e))
            return

        # ── GeoPackage : demander le nom du fichier unique ─────────────────
        if fmt == "gpkg":
            gpkg_path = self._ask_gpkg_path(output_dir, prefix)
            if not gpkg_path:
                return

        os.makedirs(output_dir, exist_ok=True)
        self.set_controls_enabled(False)
        self.log_area.clear()
        self.progress_status.setStyleSheet("")
        self._exported = []          # (uri, name) of the files written, for "add to project"
        self._export_t0 = time.time()
        if prefix:
            self.log(self.t('prefix_log', prefix=prefix))
        if zone is not None:
            area = self._fmt_area(zone_area_m2(zone[0], zone[1]))
            mode = self.rb_clip.text() if self.rb_clip.isChecked() else self.rb_whole.text()
            self.log(self.t('zone_log', desc=f"{zone[2]}, {area}", mode=mode if self.lang == 'de' else mode.lower()))

        # ── DXF fichier unique : chemin dédié ─────────────────────────────
        if fmt == DXF_SINGLE_FORMAT:
            self._run_export_dxf_single(selected_layers, output_dir, crs_code, zone, prefix)
            return

        total = len(selected_layers)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        errors = 0

        self.log(self.t('export_start', total=total))

        gpkg_layer_count = 0   # nombre de couches déjà écrites dans le GPKG

        for i, layer in enumerate(selected_layers):
            safe_name   = sanitize_filename(layer.name())
            output_path = os.path.join(output_dir, prefix + safe_name + "." + fmt)

            self.progress_status.setText(
                self.t('in_progress', name=layer.name(), i=i+1, total=total)
            )
            self.log(f"▶  {layer.name()}  [{layer.dataProvider().name()}]")

            if fmt in NO_GEOM_FORMATS:
                self.log(self.t('warn_no_geom'))

            QApplication.processEvents()

            try:
                # CSV / Excel : filtrés aussi, mais jamais découpés (pas de géométrie)
                export_layer = self._apply_zone(
                    layer, zone,
                    clip=self.rb_clip.isChecked() and fmt not in NO_GEOM_FORMATS)

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
                if self.chk_style.isChecked() and fmt in STYLE_FORMATS:
                    self._save_style(layer, fmt, output_path, safe_name)
                if fmt == "gpkg":
                    self._exported.append((f"{output_path}|layername={safe_name}", layer.name()))
                else:
                    self._exported.append((output_path,
                                           os.path.splitext(os.path.basename(output_path))[0]))
            except Exception as e:
                self.log(self.t('export_error', error=e))
                errors += 1

            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

        if errors == 0:
            self.progress_status.setText(self.t('export_done_ok', total=total))
        else:
            self.progress_status.setText(self.t('export_done_error', errors=errors, total=total))
            self._show_log(True)

        self._add_exported_to_project()
        self._zip_exported(output_dir, prefix)
        self.log(self.t('export_end'))
        self.set_controls_enabled(True)
        self.btn_close.setText(self.t('close_btn'))
