def classFactory(iface):
    from .export_couches import ExportCouchesPlugin
    return ExportCouchesPlugin(iface)