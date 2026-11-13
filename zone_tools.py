"""Export zone helpers: map tool to draw a polygon or a rectangle, rubber bands,
zone filtering of a layer (whole features or clipped at the zone limit).

Works with QGIS 3 (Qt5) and QGIS 4 (Qt6).
"""

from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsDistanceArea, QgsFeatureRequest, QgsGeometry, QgsPointXY,
                       QgsProject, QgsRectangle, QgsVectorLayer, QgsWkbTypes)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor


ZONE_STROKE = QColor(230, 81, 0)
ZONE_FILL   = QColor(230, 81, 0, 45)


def _geometry_type(name):
    """'Polygon' / 'Line' / 'Point' → enum valid on QGIS 3.30+ and QGIS 4."""
    gt = getattr(Qgis, 'GeometryType', None)
    if gt is not None and hasattr(gt, name):
        return getattr(gt, name)
    return getattr(QgsWkbTypes, name + 'Geometry')


POLYGON_TYPE = _geometry_type('Polygon')


def make_rubber_band(canvas, dashed=False):
    rb = QgsRubberBand(canvas, POLYGON_TYPE)
    rb.setStrokeColor(ZONE_STROKE)
    rb.setFillColor(ZONE_FILL)
    rb.setWidth(2)
    if dashed:
        rb.setLineStyle(Qt.PenStyle.DashLine)
    return rb


def remove_rubber_band(canvas, rb):
    if rb is None:
        return
    try:
        rb.reset(POLYGON_TYPE)
        canvas.scene().removeItem(rb)
    except RuntimeError:
        pass


# ── Map tool ──────────────────────────────────────────────────────────────────

class ZoneMapTool(QgsMapTool):
    """Draws an export zone on the canvas.

    mode 'polygon'   : left click = vertex, right click / double click = close,
                       Backspace = remove last vertex, Esc = cancel.
    mode 'rectangle' : click-drag-release, Esc = cancel.

    Signals: zoneDrawn(QgsGeometry in canvas CRS), canceled(bool restore_tool).
    canceled(False) is emitted when the user picks another map tool while drawing.
    """

    zoneDrawn = pyqtSignal(object)
    canceled  = pyqtSignal(bool)

    def __init__(self, canvas, mode='polygon'):
        super().__init__(canvas)
        self.mode = mode
        self._points = []
        self._start = None
        self._done = False
        self._rb = make_rubber_band(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ── drawing helpers ──
    def _redraw(self, extra=None):
        self._rb.reset(POLYGON_TYPE)
        pts = list(self._points)
        if extra is not None:
            pts.append(extra)
        for i, p in enumerate(pts):
            self._rb.addPoint(p, i == len(pts) - 1)

    def _rect_points(self, a, b):
        return [QgsPointXY(a.x(), a.y()), QgsPointXY(b.x(), a.y()),
                QgsPointXY(b.x(), b.y()), QgsPointXY(a.x(), b.y())]

    def _clear(self):
        self._points = []
        self._start = None
        self._rb.reset(POLYGON_TYPE)

    def _finish_polygon(self):
        pts = []
        for p in self._points:              # double click adds duplicates
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) < 3:
            self._cancel(True)
            return
        geom = QgsGeometry.fromPolygonXY([pts + [pts[0]]])
        if not geom.isGeosValid():
            geom = geom.makeValid()
        self._emit(geom)

    def _emit(self, geom):
        self._done = True
        self._clear()
        self.zoneDrawn.emit(geom)

    def _cancel(self, restore):
        self._done = True
        self._clear()
        self.canceled.emit(restore)

    # ── events ──
    def canvasPressEvent(self, e):
        if self.mode == 'rectangle' and e.button() == Qt.MouseButton.LeftButton:
            self._start = e.mapPoint()

    def canvasMoveEvent(self, e):
        if self.mode == 'rectangle':
            if self._start is not None:
                self._points = self._rect_points(self._start, e.mapPoint())
                self._redraw()
        elif self._points:
            self._redraw(e.mapPoint())

    def canvasReleaseEvent(self, e):
        if self.mode == 'rectangle':
            if e.button() != Qt.MouseButton.LeftButton or self._start is None:
                return
            a, b = self._start, e.mapPoint()
            rect = QgsRectangle(a, b)
            if rect.width() <= 0 or rect.height() <= 0:   # simple click
                self._clear()
                return
            self._emit(QgsGeometry.fromRect(rect))
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._points.append(QgsPointXY(e.mapPoint()))
            self._redraw()
        elif e.button() == Qt.MouseButton.RightButton:
            self._finish_polygon()

    def canvasDoubleClickEvent(self, e):
        if self.mode == 'polygon' and e.button() == Qt.MouseButton.LeftButton:
            self._finish_polygon()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._cancel(True)
            e.accept()
        elif e.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete) and self._points \
                and self.mode == 'polygon':
            self._points.pop()
            self._redraw()
            e.accept()

    def deactivate(self):
        # Another map tool picked while drawing → give the dialog back
        if not self._done:
            self._done = True
            self._clear()
            self.canceled.emit(False)
        super().deactivate()

    def cleanup(self):
        remove_rubber_band(self.canvas(), self._rb)
        self._rb = None


# ── Zone helpers ──────────────────────────────────────────────────────────────

def zone_area_m2(geom, crs):
    """Ellipsoidal area in m² of a geometry expressed in crs."""
    project = QgsProject.instance()
    da = QgsDistanceArea()
    da.setSourceCrs(crs, project.transformContext())
    ellipsoid = project.ellipsoid()
    da.setEllipsoid(ellipsoid if ellipsoid and ellipsoid.upper() != 'NONE' else 'EPSG:7019')
    try:
        return da.measureArea(geom)
    except Exception:
        return geom.area()


def metric_crs_for(geom, crs):
    """Projected CRS to buffer in metres: crs itself, the project CRS, or UTM."""
    if not crs.isGeographic():
        return crs
    pcrs = QgsProject.instance().crs()
    if pcrs.isValid() and not pcrs.isGeographic():
        return pcrs
    c = geom.centroid().asPoint()
    zone = int((c.x() + 180) // 6) + 1
    zone = min(max(zone, 1), 60)
    return QgsCoordinateReferenceSystem(f"EPSG:{(32600 if c.y() >= 0 else 32700) + zone}")


def transform_geometry(geom, src_crs, dst_crs):
    """Copy of geom transformed src → dst, densified so straight edges stay faithful."""
    g = QgsGeometry(geom)
    if src_crs == dst_crs:
        return g
    if g.constGet().nCoordinates() < 400:
        g = g.densifyByCount(16)
    ct = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
    g.transform(ct)
    return g


def _copy_style(src, dst):
    """Renderer + labels of src onto the memory copy (needed for DXF fidelity)."""
    try:
        if src.renderer() is not None:
            dst.setRenderer(src.renderer().clone())
        if src.labeling() is not None:
            dst.setLabeling(src.labeling().clone())
        dst.setLabelsEnabled(src.labelsEnabled())
        dst.setOpacity(src.opacity())
    except (AttributeError, RuntimeError):   # no renderer / C++ object already deleted
        pass


def filter_layer_by_zone(layer, zone_geom, zone_crs, clip=False):
    """Memory copy of layer with only the features touching the zone.

    clip=False : whole features intersecting the zone.
    clip=True  : geometries cut at the zone limit (output becomes multipart).
    Returns (memory_layer, kept_count, examined_count).
    """
    zone = transform_geometry(zone_geom, zone_crs, layer.crs())
    if not zone.isGeosValid():
        zone = zone.makeValid()

    wkb      = layer.wkbType()
    geom_typ = QgsWkbTypes.geometryType(wkb)
    if geom_typ == _geometry_type('Point'):
        clip = False                      # a point is inside or not: keep its type
    out_wkb  = QgsWkbTypes.multiType(wkb) if clip else wkb
    has_z    = QgsWkbTypes.hasZ(out_wkb)
    has_m    = QgsWkbTypes.hasM(out_wkb)

    mem = QgsVectorLayer(QgsWkbTypes.displayString(out_wkb), layer.name(), "memory")
    mem.setCrs(layer.crs())
    prov = mem.dataProvider()
    prov.addAttributes(layer.fields().toList())
    mem.updateFields()
    _copy_style(layer, mem)

    engine = QgsGeometry.createGeometryEngine(zone.constGet())
    engine.prepareGeometry()

    request = QgsFeatureRequest().setFilterRect(zone.boundingBox())
    kept, examined = [], 0
    for f in layer.getFeatures(request):
        examined += 1
        g = f.geometry()
        if g.isNull() or g.isEmpty():
            continue
        if not engine.intersects(g.constGet()) or engine.touches(g.constGet()):
            continue                      # outside, or only touching the limit
        if clip:
            if engine.contains(g.constGet()):
                ng = QgsGeometry(g)
            else:
                ng = g.intersection(zone)
                if ng.isNull() or ng.isEmpty():
                    ng = g.makeValid().intersection(zone)
                if ng.isNull() or ng.isEmpty():
                    continue
                if ng.type() != geom_typ:       # GeometryCollection, lower dimension…
                    ng = ng.convertToType(geom_typ, True)
                    if ng is None or ng.isNull() or ng.isEmpty():
                        continue
            ng.convertToMultiType()
            if has_z and not ng.constGet().is3D():
                ng.get().addZValue(0)
            if has_m and not ng.constGet().isMeasure():
                ng.get().addMValue(0)
            f.setGeometry(ng)
        kept.append(f)

    prov.addFeatures(kept)
    mem.updateExtents()
    return mem, len(kept), examined
