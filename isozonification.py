# -*- coding: utf-8 -*-
"""
/***************************************************************************
 isozonification
                                 A QGIS plugin
 Divide in zones/clusters of polygons using an attrinbute
                              -------------------
        begin                : 2015-06-08
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Nacho Varela
        email                : nachouve@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from isozonification_dialog import isozonificationDialog
import os.path

import sys

from qgis.core import QgsMapLayerRegistry, QgsMapLayer

##TODO How is the proper way to add this library??
from pygraph.classes import *
#from pygraph.classes.graph import graph


class isozonification:
    """QGIS Plugin Implementation."""

    #Layer to process
    layer = None
    #Layer field to use
    field = None
    #Number of zones to group
    numZones = 3

    mygraph = None

    def myprint(msg):
        print "myprint: [%s]" % msg

    def guiLoadAttributesOnComboBox(obj):
        index = obj.dlg.layerCBox.currentIndex()
        layer = obj.dlg.layerCBox.itemData(index)

        if not layer:
            return
        #TODO
        #clean ComboBox first!!!

        for field in layer.pendingFields():
            print "field: %s (%s)" % (field.name(), field.typeName())
            if field.typeName() == 'Integer': #and layer.geometryType() == QGis.Line:
               obj.dlg.attrCBox.addItem( field.name(), field.name() )


    def guiLoadLayersOnComboBox(self):
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            print "layer: %s" % layer.name()
            if layer.type() == QgsMapLayer.VectorLayer: #and layer.geometryType() == QGis.Line:
               self.dlg.layerCBox.addItem( layer.name(), layer ) 

        self.dlg.layerCBox.currentIndexChanged['QString'].connect(self.guiLoadAttributesOnComboBox)


    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'isozonification_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = isozonificationDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&isozonification')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'isozonification')
        self.toolbar.setObjectName(u'isozonification')


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('isozonification', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/isozonification/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Iso Zonification'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&isozonification'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def doSomethingUtil(self):
        index = self.dlg.layerCBox.currentIndex()
        layer = self.dlg.layerCBox.itemData(index)
        self.layer = layer

        index = self.dlg.attrCBox.currentIndex()
        self.field = self.dlg.attrCBox.itemData(index)

        try:
            self.numZones = int(self.dlg.zonesNumLineEdit.text())
        except:
            pass

        if not self.layer or not self.field or not self.numZones:
            return

        response = QMessageBox.information(self.iface.mainWindow(),"IsoZonification", 
            "%s has %d features.\n \
            Create %d zones.\n\
            Mean %f features per zone" % 
            (layer.name(), layer.featureCount(), self.numZones, layer.featureCount()/self.numZones))

        # Prepare graph
        self.mygraph = graph()

    def run(self):
        """Run method that performs all the real work"""

        self.guiLoadLayersOnComboBox()
        self.guiLoadAttributesOnComboBox()
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            ##TODO
            # Ensure num zones is logical (1, #features)
            self.doSomethingUtil()
