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

from qgis.core import QgsMapLayerRegistry, QgsMapLayer, QgsFeatureRequest, QgsVectorDataProvider

##TODO How is the proper way to add this library??
## Manually install in the python2.7 path:
## https://github.com/pmatiello/python-graph 
from pygraph.classes.graph import graph as Graph

DEBUG = True

class isozonification:
    """QGIS Plugin Implementation."""

    #Layer to process
    layer = None
    #Layer field to use
    field = None
    #Number of zones to group
    numZones = 3
    
    ZONES = dict()

    ## TODO. Now the vector layer must have "ZONE_ID" field
    zone_field = "ZONE_ID"

    mygraph = None

    def myprint(msg):
        print "myprint: [%s]" % msg

    def guiLoadAttributesOnComboBox(obj):
        obj.dlg.attrCBox.clear()
        
        index = obj.dlg.layerCBox.currentIndex()
        layer = obj.dlg.layerCBox.itemData(index)

        if not layer:
            return

        for field in layer.pendingFields():
            #if DEBUG: print "field: %s (%s)" % (field.name(), field.typeName())
            if field.typeName() == 'Integer': #and layer.geometryType() == QGis.Line:
               obj.dlg.attrCBox.addItem( field.name(), field.name() )


    def guiLoadLayersOnComboBox(self):
        
        self.dlg.attrCBox.clear()
        
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            if DEBUG: print "layer: %s" % layer.name()
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


    def createGraph(self):
        """
        Create the self.mygraph to group
        
        Return a list of featureIds
        """
        
        ids = []
        
        # Prepare graph
        self.mygraph = Graph()
        
        
        ## Create Nodes
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            value = feat[self.field]
            
            self.mygraph.add_node(id, attrs= [('event', value)] )
            
            ids.append(id)
        
        
        # Create Edges
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            value = feat[self.field]
         
            if DEBUG: print "****** %d *****" % id 
            if DEBUG: print "Field: " + str(value)
            
            filter = QgsFeatureRequest().setFlags(QgsFeatureRequest.ExactIntersect).setFilterRect(feat.geometry().boundingBox())
            iter2 = self.layer.getFeatures(filter)
            for feat2 in iter2:
                id2 = feat2.id()                
                if (id != id2):
                    try:
                        self.mygraph.add_edge((id, id2))
                        if DEBUG: print "- " + str(id2)
                    except Exception, e:
                        #if DEBUG: print e
                        pass
        return ids
    
    def getRealNodeOrder(self, feat_id, possible_ids):
        curr_order = 0
        neighbors = [] 
        for i in self.mygraph.neighbors(feat_id):
            if i in possible_ids:
                neighbors.append(i)
        
        return len(set(neighbors))
                    
    def getNextFeat(self, possible_ids, not_zero_order=True):
        """
        "not_zero_order" to avoid isles
        """
        selected_id = None
        min_order = -1
        
        if possible_ids == None or len(possible_ids) ==0:
            print "No more possible features"
            return None
        
        for feat_id in possible_ids:
            curr_order = self.getRealNodeOrder(feat_id, possible_ids)
            if DEBUG>1: print "RealNodeOrder(%d): %d" % (feat_id, curr_order)
            if not_zero_order and curr_order == 0:
                continue
            if selected_id == None or curr_order < min_order:
                selected_id = feat_id
                min_order = curr_order
        if (selected_id and min_order):
            if DEBUG: print "Next feat: %d (%d)" % (selected_id, min_order)
        else:
            if DEBUG: print "ERRRRRORRRRRRRRR (getNextFeat): "
            if DEBUG: print "    selected_id:" + str(selected_id)
            if DEBUG: print "    min_order:" + str(min_order)
            
        return selected_id
    
    def summatory(self):
        sum = 0
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            sum += int(feat[self.field])
        return sum
    
    def check_if_zone_complete(self, zone):
        TOLERANCE = 0.8
        
        if DEBUG: print "zone event_count: %d (%d) " % (zone["event_count"], self.MEAN_EVENTS_PER_ZONE)
        
        if (float(zone["event_count"])/self.MEAN_EVENTS_PER_ZONE) > TOLERANCE:
            return True
        
        return False


    def resetField(self, layer, fieldName):
        caps = self.layer.dataProvider().capabilities()
        if caps & QgsVectorDataProvider.ChangeAttributeValues:
            attrs = { layer.fieldNameIndex (fieldName) : None }
            iter = layer.getFeatures()
            for feat in iter:
                id = feat.id()
                layer.dataProvider().changeAttributeValues({ id : attrs })

    def getAdjacents(self, zone, possible_feats=None):
        
        adj_list = list()
        
        for i in zone["features"]:
            neighborgs = self.mygraph    .neighbors(i)
            if DEBUG > 1: print "features [%d] has %d neighbors" % (i, len(neighborgs))
            adj_list.extend(neighborgs)
            
        #if DEBUG: print "   Possible_feats:"
        #if DEBUG: print str(possible_feats)
        
        new_adj_list = []
        adj_list = list(set(adj_list))
        
        if DEBUG: print "Current adj_list: " + str(adj_list)
        
        if possible_feats:
            for i in adj_list:
                #if DEBUG: print "Checking %d" % i
                if i in possible_feats:
                    new_adj_list.append(i)
                #else:
                #    if DEBUG: print "Remove adjacent (already in zone): " + str(i)
        else:
            new_adj_list = adj_list
        return new_adj_list
    
    
    def getMinorZone(self, adjacents):
        
        min_event_count = None
        min_zone = None
        adjacent_zones = list()
        for i in self.ZONES:
            if DEBUG: print "Zone: " + str(i)
            zone_feats = self.ZONES[i]["features"]
            for a in adjacents:
                if a in zone_feats:
                    adjacent_zones.append(i)
                    zone_event_count = self.ZONES[i]["event_count"]
                    if (min_event_count == None) or zone_event_count < min_event_count:
                        min_event_count = zone_event_count 
                        min_zone = i
                    break
        return min_zone
    
    def assignFeat2Zone(self, feat_id, event_value, zone_id):
        caps = self.layer.dataProvider().capabilities()

        if caps & QgsVectorDataProvider.ChangeAttributeValues:
            attrs = {self.layer.fieldNameIndex ( self.zone_field) : zone_id }
            self.layer.dataProvider().changeAttributeValues({ feat_id : attrs })
            
            if zone_id in self.ZONES:
                old_features = self.ZONES[zone_id]["features"]
                old_event_count = self.ZONES[zone_id]["event_count"]
                old_features.append(feat_id) 
                self.ZONES[zone_id] = { "features": old_features, "event_count": event_value+old_event_count }
            else:
                self.ZONES[zone_id] = { "features": [feat_id], "event_count": event_value }
            
            if DEBUG: print "assignFeat2Zone Zone: %s  --> %s " % (str(zone_id), str(self.ZONES[zone_id]))
        
        #self.iface.mapCanvas().refresh() #nothing happened
        self.layer.triggerRepaint()
        #response = QMessageBox.information(self.iface.mainWindow(),"IsoZonification", "Refreshed")

    
    def assignIsle(self, feat_id, value):
        
        zone = {"features": [feat_id]}
        
        adjacents = self.getAdjacents(zone)
        
        if DEBUG: print "Isle can be assign to: " + str(adjacents)
        
        zone_to_assign = self.getMinorZone(adjacents)
        
        if DEBUG: print "Min Adjacent Zone: %s" % str(zone_to_assign)
        
        self.assignFeat2Zone(feat_id, value, zone_to_assign)
        
    
    def check_isles(self):
        """
        Assign isle features to a zone
        """
        print "\n====================================="
        if DEBUG: print "Checking isles..."
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            value = feat[self.field]
            zone = feat[self.zone_field]
            if (zone == None):
                if DEBUG: print "Feat [%d] is a isle" % id
                self.assignIsle(id, value)


    def doSomethingUtil(self):
        
        self.resetField(self.layer, self.zone_field)

        self.ZONES = dict()
        
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
        
#         response = QMessageBox.information(self.iface.mainWindow(),"IsoZonification", 
#             "%s has %d features.\n \
#             Create %d zones.\n\
#             Mean %f features per zone" % 
#             (layer.name(), layer.featureCount(), self.numZones, layer.featureCount()/self.numZones))

        free_feats = self.createGraph()
        if DEBUG: print free_feats
        
        ZONE_COUNT = 0
        
        
        self.MEAN_FEAT_PER_ZONE = layer.featureCount()/self.numZones
        self.MEAN_EVENTS_PER_ZONE = self.summatory()/self.numZones
        
        print "MEAN_FEAT_PER_ZONE: %d" % self.MEAN_FEAT_PER_ZONE
        print "MEAN_EVENTS_PER_ZONE: %d" % self.MEAN_EVENTS_PER_ZONE
        
        MAX_ITERATIONS = 500
        
        ##############################
        ## FIRST ELEMENT
        ### ToDo sort by Cardinality and numerical
        
        active_feat_id = self.getNextFeat(free_feats)
        
        ##############################
        
        iteration_count = 0
        
        while ZONE_COUNT < self.numZones and \
              len(free_feats) > 0 and \
              iteration_count < MAX_ITERATIONS:
                        
            if DEBUG: print "> Active ID: %s" % str(active_feat_id)
            if DEBUG: print "free_feats:"
            if DEBUG: print str(free_feats)
            
            if active_feat_id == None:
                if DEBUG: print "active_feat_id NONE"
                break
            
            event_value = self.mygraph.node_attributes(active_feat_id)
            event_value = event_value[0][1]
            if DEBUG: print "event value: " + str(event_value)
            
            
            ## TODO Change to method --> http://lists.osgeo.org/pipermail/qgis-developer/2013-October/028808.html
        
            self.assignFeat2Zone(active_feat_id, event_value, ZONE_COUNT)
            if DEBUG: print ">>>>>>>>> ADDED %d to ZONE [%d]" % (active_feat_id, ZONE_COUNT)
            
            if active_feat_id in free_feats:
                if DEBUG: print "Remove [%d] from free_feat list " % active_feat_id
                free_feats.remove(active_feat_id)
        
            zone_completed = self.check_if_zone_complete(self.ZONES[ZONE_COUNT])
            has_adjacents = False
            adjacents = None

            if not zone_completed:
                adjacents = self.getAdjacents(self.ZONES[ZONE_COUNT], free_feats)
                if DEBUG: print "Adjacents: " + str(adjacents)
            
            if adjacents and len(adjacents) > 0:
                active_feat_id = self.getNextFeat(adjacents)

            if active_feat_id == None:
                if DEBUG: print "No NextFeat(Adjacents): " + str(active_feat_id)
                zone_completed = True            

            if zone_completed:
                ZONE_COUNT += 1
                if DEBUG: print "*************** NEW ZONE %d **************" % ZONE_COUNT
                active_feat_id = self.getNextFeat(free_feats)
            
            iteration_count += 1
            
        
        self.check_isles()
        
        self.print_zones()
        
    def print_zones(self):
        print "\n====================================="
        for zone in self.ZONES:
            print "\nZONE %s" % str(zone)
            print "---------------------"
            print "Features: " + str(self.ZONES[zone]["features"])
            print "Count: " + str(self.ZONES[zone]["event_count"])
            
            

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
