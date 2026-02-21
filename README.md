# Export Couches Vecteur — Vector Layer Export

> Plugin QGIS · v1.2.0 · QGIS 3.x · Bilingue FR / EN

---

## Français

### Description

**Export Couches Vecteur** est un plugin QGIS qui vous permet d'exporter en un clic l'ensemble (ou une sélection) de vos couches vecteur dans le format de votre choix, avec reprojection optionnelle et suivi de progression en temps réel.

Fini les allers-retours dans les menus : ouvrez le plugin, cochez vos couches, choisissez votre format et votre dossier de sortie — et laissez le plugin faire le reste.

### Fonctionnalités

- **11 formats d'export** : GeoJSON, Shapefile, GeoPackage, CSV, Excel (XLSX), KML, GML, FlatGeobuf, MapInfo TAB, SQLite, DXF
- **Reprojection à la volée** : Lambert-93 (EPSG:2154), WGS 84 (EPSG:4326), Web Mercator (EPSG:3857), ou conservation du CRS d'origine
- **Sélection flexible** : cochez / décochez les couches individuellement ou via les boutons *Tout sélectionner* / *Tout désélectionner*
- **Barre de progression** et journal en temps réel pour suivre chaque export
- **Export DXF intelligent** : les polygones sont automatiquement convertis en contours (lignes) pour assurer la compatibilité DXF
- **Interface bilingue** : basculez entre le français et l'anglais d'un simple clic, sans redémarrer le plugin
- Un fichier par couche, nommé automatiquement d'après le nom de la couche

### Installation

1. Téléchargez ou clonez ce dépôt :

   ```bash
   git clone https://github.com/yoanl/Export_multilayers.git
   ```

2. Copiez le dossier `Export_multilayers` dans le répertoire des plugins QGIS :

   | Système | Chemin |
   |---------|--------|
   | Windows | `C:\Users\<utilisateur>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\` |
   | macOS   | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |
   | Linux   | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |

3. Ouvrez QGIS, allez dans **Extensions → Installer/Gérer les extensions**, cochez **Export Couches Vecteur** et cliquez sur **OK**.

4. Une icône apparaît dans la barre d'outils et un menu **Export Couches Vecteur** est ajouté.

### Utilisation

Imaginez que vous avez un projet QGIS bien rempli — des dizaines de couches, des données en tout genre, et votre chef vous demande *"tu peux m'envoyer tout ça en Shapefile pour ce soir ?"*. Pas de panique !

1. **Lancez le plugin** via la barre d'outils ou le menu **Extensions → Export Couches Vecteur**.
2. **Sélectionnez vos couches** : toutes les couches vecteur du projet apparaissent cochées par défaut. Décochez celles que vous voulez ignorer.
3. **Choisissez votre format** : GeoJSON pour votre équipe web, Shapefile pour votre client old-school, DXF pour votre collègue sous AutoCAD...
4. **Choisissez votre CRS** : reprojetez à la volée ou conservez le CRS d'origine.
5. **Indiquez le dossier de sortie** avec le bouton *Parcourir...*.
6. Cliquez sur **Exporter** et regardez la barre de progression avancer.
7. Consultez le **journal** pour vérifier que tout s'est bien passé (coches vertes ✔ ou alertes ⚠).

> **Astuce** : les formats CSV et Excel n'exportent que les attributs, pas la géométrie. Le plugin vous en avertit dans le journal.

### Formats supportés

| Format | Extension | Géométrie |
|--------|-----------|-----------|
| GeoJSON | `.geojson` | ✔ |
| Shapefile | `.shp` | ✔ |
| GeoPackage | `.gpkg` | ✔ |
| KML | `.kml` | ✔ |
| GML | `.gml` | ✔ |
| FlatGeobuf | `.fgb` | ✔ |
| MapInfo TAB | `.tab` | ✔ |
| SQLite | `.sqlite` | ✔ |
| DXF | `.dxf` | ✔ (géométrie seule) |
| CSV | `.csv` | ✘ (attributs seuls) |
| Excel | `.xlsx` | ✘ (attributs seuls) |

---

## English

### Description

**Vector Layer Export** is a QGIS plugin that lets you export all (or a selection) of your vector layers in your chosen format, with optional reprojection and real-time progress tracking — all from a single, clean dialog.

No more digging through menus: open the plugin, check your layers, pick a format and output folder, and let the plugin handle the rest.

### Features

- **11 export formats**: GeoJSON, Shapefile, GeoPackage, CSV, Excel (XLSX), KML, GML, FlatGeobuf, MapInfo TAB, SQLite, DXF
- **On-the-fly reprojection**: Lambert-93 (EPSG:2154), WGS 84 (EPSG:4326), Web Mercator (EPSG:3857), or keep original CRS
- **Flexible selection**: check / uncheck layers individually or use *Select all* / *Deselect all* buttons
- **Progress bar** and real-time log to track every export
- **Smart DXF export**: polygons are automatically converted to outlines (lines) for DXF compatibility
- **Bilingual interface**: switch between French and English in one click, no restart needed
- One file per layer, automatically named after the layer name

### Installation

1. Download or clone this repository:

   ```bash
   git clone https://github.com/yoanl/Export_multilayers.git
   ```

2. Copy the `Export_multilayers` folder to your QGIS plugins directory:

   | OS | Path |
   |----|------|
   | Windows | `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\` |
   | macOS   | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |
   | Linux   | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |

3. Open QGIS, go to **Plugins → Manage and Install Plugins**, check **Export Couches Vecteur** and click **OK**.

4. An icon appears in the toolbar and a **Export Couches Vecteur** menu is added.

### Usage

Picture this: your QGIS project is packed with dozens of layers and your manager just asked *"can you send me all of that as Shapefiles by tonight?"*. No stress!

1. **Launch the plugin** from the toolbar or the **Plugins → Export Couches Vecteur** menu.
2. **Select your layers**: all vector layers in the project appear pre-checked. Uncheck the ones you want to skip.
3. **Choose your format**: GeoJSON for your web team, Shapefile for your old-school client, DXF for your AutoCAD colleague...
4. **Choose your CRS**: reproject on the fly or keep the original CRS.
5. **Set the output folder** using the *Browse...* button.
6. Click **Export** and watch the progress bar fill up.
7. Check the **log** to confirm everything went smoothly (green ticks ✔ or warnings ⚠).

> **Tip**: CSV and Excel formats export attributes only — no geometry. The plugin will warn you in the log.

### Supported Formats

| Format | Extension | Geometry |
|--------|-----------|----------|
| GeoJSON | `.geojson` | ✔ |
| Shapefile | `.shp` | ✔ |
| GeoPackage | `.gpkg` | ✔ |
| KML | `.kml` | ✔ |
| GML | `.gml` | ✔ |
| FlatGeobuf | `.fgb` | ✔ |
| MapInfo TAB | `.tab` | ✔ |
| SQLite | `.sqlite` | ✔ |
| DXF | `.dxf` | ✔ (geometry only) |
| CSV | `.csv` | ✘ (attributes only) |
| Excel | `.xlsx` | ✘ (attributes only) |

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| **1.2.0** | 2025 | Correction de l'export DXF via `QgsVectorFileWriter` — conversion automatique des polygones en contours |
| **1.1.0** | 2025 | Ajout des formats DXF, KML, GML, FlatGeobuf, TAB, SQLite, Excel — interface bilingue FR/EN |
| **1.0.0** | 2025 | Version initiale |

---

## Auteur · Author

Développé par / Developed by **Yoan Laloux**

Technicien SIG — Vichy Communauté
GIS Technician — Vichy Communauté

- Courriel / Email : [y.laloux@vichy-communaute.fr](mailto:y.laloux@vichy-communaute.fr)

Concept et idée originale par Yoan Laloux — développé avec l'assistance d'outils d'IA générative.
Concept and original idea by Yoan Laloux — developed with the assistance of generative AI tools.

---

## Licence · License

Ce projet est distribué sous licence **GNU General Public License v2.0**, conformément aux exigences de l'écosystème de plugins QGIS.

This project is distributed under the **GNU General Public License v2.0**, in line with the QGIS plugin ecosystem requirements.
