# -*- coding: utf-8 -*-
"""
/***************************************************************************
 equicluster
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
from equicluster_dialog import equiclusterDialog
import os.path

import sys

from qgis.core import QgsMapLayerRegistry, QgsMapLayer, QgsFeatureRequest, QgsVectorDataProvider

from random import random
from operator import itemgetter, attrgetter, methodcaller

DEBUG = 0

class equicluster:
    """QGIS Plugin Implementation

    Algorithm has a random component, so it can be differents results between executions
    """

    #Layer to process
    layer = None
    #Layer field to use
    field = None
    #Number of zones to group
    numZones = 3
    # Percentage to change zone
    TOLERANCE = 0.85
    
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
        
        self.dlg.layerCBox.clear()
        
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
            'equicluster_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = equiclusterDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&equicluster')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'equicluster')
        self.toolbar.setObjectName(u'equicluster')


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
        return QCoreApplication.translate('equicluster', message)


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

        icon_path = ':/plugins/equicluster/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'EquiCluster'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&equicluster'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def createGraph(self):
        """
        Create the self.mygraph to group
        
        Return a list of featureIds
        """
        
        ##TODO How is the proper way to add this library??
        ## Manually install in the python2.7 path:
        ## https://github.com/pmatiello/python-graph 
        from pygraph.classes.graph import graph
        
        ids = []
        
        # Prepare graph
        self.mygraph = graph()
        
        
        ## Create Nodes
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            value = feat[self.field]
            self.mygraph.add_node(id, attrs= [('event', value), ('geom',feat.geometry().centroid())] )
            ids.append(id)
        
        # Create Edges
        iter = self.layer.getFeatures()
        for feat1 in iter:
            id1 = feat1.id()
            geom1 = feat1.geometry()
            value = feat1[self.field]
         
            if DEBUG>4: print "****** %d *****" % id1
            if DEBUG>4: print "Field: " + str(value)
            
            filter2 = QgsFeatureRequest().setFilterRect(geom1.buffer(10, 4).boundingBox())
            iter2 = self.layer.getFeatures(filter2)
            for feat2 in iter2:
                id2 = feat2.id()
                if (id1 != id2):
                    touches = geom1.touches(feat2.geometry())
                    #if DEBUG>5: print "Check id2: %d (%.3f)" % (id2,dist)
                    if not touches:
                        continue
                    try:
                        self.mygraph.add_edge((id1, id2))
                        if DEBUG>5: print "- " + str(id2)
                    except Exception, e:
                        if DEBUG>5: print e
                        pass
        return ids
    
    def getRealNodeOrder(self, feat_id, possible_ids):
        curr_order = 0
        neighbors = [] 
        if DEBUG>1: print "%d has %d neighbors" % (feat_id, len(self.mygraph.neighbors(feat_id)))
        for i in self.mygraph.neighbors(feat_id):
            if i in possible_ids:
                neighbors.append(i)
        
        return len(set(neighbors))
    
    
    def getMinorOrderList(self, possible_ids, free_feats, not_zero_order=True):
        ordered_possible_ids = []
        
        for feat_id in possible_ids:
            curr_order = self.getRealNodeOrder(feat_id, free_feats)
            if DEBUG>1: print "RealNodeOrder(%d): %d" % (feat_id, curr_order)
            if not_zero_order and curr_order == 0:
                continue
            ordered_possible_ids.append((feat_id, curr_order))
        
        ordered_possible_ids = sorted(ordered_possible_ids, key=itemgetter(1))
        return ordered_possible_ids

    def getFarthest(self, possible_ids):
        selected_id = None
        max_dist = -1
        
        for zone_id in self.ZONES:
            ## Just get 1 feat (speed)
            zone_feat = self.ZONES[zone_id]["features"][0]
            node_attributes = self.mygraph.node_attributes(zone_feat)
            geom1 = node_attributes[1][1]
            for feat_id in possible_ids:
                node_attributes = self.mygraph.node_attributes(feat_id)
                geom2 = node_attributes[1][1]
                dist = geom1.distance(geom2)
                if selected_id == None or dist > max_dist:
                    selected_id = feat_id
                    max_dist = dist
        
        return selected_id
        

    def getNearest(self, current_zone_id, possible_ids):
        selected_id = None
        min_dist = -1

        zone_feats = self.ZONES[current_zone_id]["features"]
        for possible_id in possible_ids:
            node_attributes = self.mygraph.node_attributes(possible_id)
            geom1 = node_attributes[1][1]
            if DEBUG>5: print "    nearest geom1:" + str(geom1.exportToWkt())
            dist = 0
            for zone_feat_id in zone_feats:
                node_attributes = self.mygraph.node_attributes(zone_feat_id)
                geom2 = node_attributes[1][1]
                dist += geom1.distance(geom2)
                if DEBUG>5: print "    nearest geom2:" + str(geom2.exportToWkt())
            if selected_id == None or dist < min_dist:
                selected_id = possible_id
                min_dist = dist

        return selected_id
                    
    def getNextFeat(self, current_zone_id, possible_ids, free_feats, not_zero_order=True):
        """
        "not_zero_order" to avoid isles
        """
        if DEBUG: print "Select NextFeat for zone: " + str(current_zone_id)
        WEIGHT_MINORDER = 10
        #Get getting a new one
        WEIGHT_RANDOM = 30
        
        minor_order_id = None 
        neasert_id = None
        farthest_id = None

        if possible_ids == None or len(possible_ids) ==0:
            print "No more possible features"
            return None
        
        minor_order_ids = self.getMinorOrderList(possible_ids, free_feats, not_zero_order)
        
        if len(minor_order_ids)>0:
            minor_order_id = minor_order_ids[0][0]
        else:
            if DEBUG: print "ERRRRRORRRRRRRRR (getNextFeat): "
            if DEBUG: print "    minor_order_id:" + str(None)
        
        minor_order_ids = minor_order_ids[0:(1+len(minor_order_ids))/2]
        minor_order_ids = [i[0] for i in minor_order_ids]
        farthest_id = self.getFarthest(minor_order_ids)
        
        if len(self.ZONES)>current_zone_id:
            nearest_id = self.getNearest(current_zone_id, possible_ids)
        else:
            nearest_id = farthest_id
        
        selected_id = None
        if int(random()*100) < WEIGHT_MINORDER:
            selected_id = minor_order_id
            if DEBUG: print "Selected Minor_id: " + str(selected_id)
        else:
            selected_id = nearest_id
            if DEBUG: print "Selected Nearest_id: " + str(selected_id)

        if (len(possible_ids) == len(free_feats)):
            ## New zone
            if int(random()*100) < WEIGHT_RANDOM:
                random_idx = int(random()*100)%len(possible_ids)
                selected_id = possible_ids[random_idx]
                if DEBUG: print "Selected random_id: " + str(selected_id)
            elif (farthest_id != None):
                selected_id = farthest_id
                if DEBUG: print "Selected Farthest_id: " + str(selected_id)
                
        if selected_id == None:
            if DEBUG: print "All nulls [nearest_id, minor_order_id, farthest_id]: " + str([nearest_id, minor_order_id, farthest_id])
            if nearest_id != None:
                selected_id = nearest_id
                if DEBUG: print "ReSelected nearest_id: " + str(selected_id)
            if minor_order_id != None:
                selected_id = minor_order_id
                if DEBUG: print "ReSelected Minor_id: " + str(selected_id)
            if farthest_id != None:
                selected_id = farthest_id
                if DEBUG: print "ReSelected farthest_id: " + str(selected_id)

        return selected_id
    
    def summatory(self):
        sum = 0
        iter = self.layer.getFeatures()
        for feat in iter:
            id = feat.id()
            sum += int(feat[self.field])
        return sum
    
    def check_if_zone_complete(self, value):
        
        if DEBUG: print "zone event_count: %d (%d) " % (value, self.MEAN_EVENTS_PER_ZONE)
        
        if (float(value)/self.MEAN_EVENTS_PER_ZONE) > self.TOLERANCE:
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
            neighborgs = self.mygraph.neighbors(i)
            if DEBUG > 1: print "features [%d] has %d neighbors" % (i, len(neighborgs))
            adj_list.extend(neighborgs)
            
        #if DEBUG: print "Possible_feats:"
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
    
    
    def getMinorZone(self, adjacents=None, exclude_zones=[]):
        
        min_event_count = None
        min_zone = None
        adjacent_zones = list()
        for i in self.ZONES:            
            if DEBUG: print "Zone: " + str(i)
            if i in exclude_zones:
                if DEBUG: print "Excluded: " + str(i)
                continue
            zone_feats = self.ZONES[i]["features"]
            if adjacents:
                for a in adjacents:
                    if a in zone_feats:
                        adjacent_zones.append(i)
                        zone_event_count = self.ZONES[i]["event_count"]
                        if (min_event_count == None) or zone_event_count < min_event_count:
                            min_event_count = zone_event_count 
                            min_zone = i
                        break
            else:
                zone_event_count = self.ZONES[i]["event_count"]
                if (min_event_count == None) or zone_event_count < min_event_count:
                    min_event_count = zone_event_count 
                    min_zone = i

        return min_zone
    
    def assignFeat2Zone(self, feat_id, event_value, zone_id, free_feats):
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
            
            if DEBUG: print "assignFeat2Zone feat [%s] Zone: %s  --> %s " % (str(feat_id),str(zone_id), str(self.ZONES[zone_id]))
            free_feats.remove(feat_id)
            if DEBUG: print "Remove [%d] from free_feat list " % feat_id

        
        self.iface.mapCanvas().refresh() #nothing happened
        self.layer.triggerRepaint()
        #response = QMessageBox.information(self.iface.mainWindow(),"EquiCluster", "Refreshed")


    def doSomethingUtil(self):        

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
            print "not self.layer or not self.field or not self.numZones"
            return
        
        if not self.zone_field in map(lambda x: x.name(), self.layer.dataProvider().fields()):
            msg = "ERROR: Layer must have a [%s] field (numeric).\n" % self.zone_field 
            response = QMessageBox.information(self.iface.mainWindow(),
                                           "EquiCluster", 
                                           msg)
            return

        self.resetField(self.layer, self.zone_field)

        self.MEAN_FEAT_PER_ZONE = float(layer.featureCount())/self.numZones
        self.MEAN_EVENTS_PER_ZONE = self.summatory()/self.numZones
        
        print "MEAN_FEAT_PER_ZONE: %d" % self.MEAN_FEAT_PER_ZONE
        print "MEAN_EVENTS_PER_ZONE: %d" % self.MEAN_EVENTS_PER_ZONE
        
        msg = "%s has %d features \n" % (layer.name(), layer.featureCount()) 
        msg += "Mean %.2f features per zone (%d zones) \n" % (self.MEAN_FEAT_PER_ZONE, self.numZones)
        msg += "Mean %.2f events per zone (>%.2f)" % (self.MEAN_EVENTS_PER_ZONE, (self.MEAN_EVENTS_PER_ZONE * self.TOLERANCE))
        response = QMessageBox.information(self.iface.mainWindow(),
                                           "EquiCluster", 
                                           msg)

        free_feats = self.createGraph()
        if DEBUG: print free_feats
        
        ZONE_COUNT = 0
        
        MAX_ITERATIONS = layer.featureCount()+10
        
        ##############################
        ## FIRST: Assign zones to features with events higher than mean 
        
        iter = self.layer.getFeatures()
        for feat in iter:
            event_value = feat[self.field]
            if (self.check_if_zone_complete(event_value)):
                fid = feat.id()
                self.assignFeat2Zone(fid, event_value, ZONE_COUNT, free_feats)
                ZONE_COUNT += 1
        
        ##############################        
        
        
        ##############################
        ## SECOND: FIRST ELEMENT
        
        active_feat_id = self.getNextFeat(ZONE_COUNT, free_feats, free_feats)
        
        ##############################
        
        iteration_count = 0
        
        while ZONE_COUNT < self.numZones and \
              len(free_feats) > 0 and \
              iteration_count < MAX_ITERATIONS:
            
            if DEBUG: print " --- Iteration %s --" % str(iteration_count)

            if DEBUG: print "> Active ID: %s" % str(active_feat_id)
            if DEBUG>2: print "free_feats:" + str(free_feats)
            
            if active_feat_id == None:
                if DEBUG: print "active_feat_id NONE"
                break
            
            node_attributes = self.mygraph.node_attributes(active_feat_id)
            event_value = node_attributes[0][1]
            if DEBUG: print "event value: " + str(event_value)
            
            
            ## TODO Change to method --> http://lists.osgeo.org/pipermail/qgis-developer/2013-October/028808.html
        
            if active_feat_id in free_feats:        
                self.assignFeat2Zone(active_feat_id, event_value, ZONE_COUNT, free_feats)
                if DEBUG: print ">>>>>>>>> ADDED %d to ZONE [%d]" % (active_feat_id, ZONE_COUNT)
                        
            zone_completed = self.check_if_zone_complete(self.ZONES[ZONE_COUNT]["event_count"])
            has_adjacents = False
            adjacents = None

            if not zone_completed:
                adjacents = self.getAdjacents(self.ZONES[ZONE_COUNT], free_feats)
                if DEBUG: print "Adjacents: " + str(adjacents)
            
            if adjacents and len(adjacents) > 0:
                active_feat_id = self.getNextFeat(ZONE_COUNT, adjacents, free_feats)
            else:
                active_feat_id = None

            if active_feat_id == None:
                if DEBUG: print "No NextFeat(Adjacents): " + str(active_feat_id)
                zone_completed = True            

            if zone_completed:
                ZONE_COUNT += 1
                if DEBUG: print "******************************************" 
                if DEBUG: print "*************** NEW ZONE %d **************" % ZONE_COUNT
                active_feat_id = self.getNextFeat(ZONE_COUNT, free_feats, free_feats)
            
            iteration_count += 1
        
        ## THIRD: ISLES
        print "\n===============  ISLES ======================"
        iteration_count = 0
        #Used to exclude zones without free adjacents
        not_use_zones = []

        free_feats = []
        iter = self.layer.getFeatures()
        for feat in iter:
            value = feat[self.zone_field]
            if (value == None):
                fid = feat.id()
                free_feats.append(fid)

        global DEBUG
        while len(free_feats) > 0 and \
              iteration_count < MAX_ITERATIONS:
            iteration_count += 1
            #DEBUG = 4
            if DEBUG: print " --- (Isle) Iteration %s --" % str(iteration_count)
            if DEBUG: print "len(free_feats): " + str(len(free_feats))
            
            min_zone = self.getMinorZone(exclude_zones=not_use_zones)

            #DEBUG = 1
            if DEBUG: print "Min zone: " + str(min_zone)
            if (min_zone == None):
                continue
            min_zone_adjacents = self.getAdjacents(self.ZONES[min_zone], possible_feats=free_feats)
            if len(min_zone_adjacents)>0:
                ##self.check_isles(min_zone_adjacents)
                #DEBUG = 3
                selected_id = self.getNextFeat(min_zone, min_zone_adjacents, free_feats)
                if selected_id != None:
                    node_attributes = self.mygraph.node_attributes(selected_id)
                    event_value = node_attributes[0][1]
                    self.assignFeat2Zone(selected_id, event_value, min_zone, free_feats)
            else:
                if DEBUG: print "Excluded: " + str(not_use_zones)
                not_use_zones.append(min_zone)
        
        self.print_zones()
        
    def print_zones(self):
        print "\n====================================="
        summary = ""
        for zone in self.ZONES:
            summary += "\nZONE %s: %d eventos (%d features)" % (str(zone), self.ZONES[zone]["event_count"], len(self.ZONES[zone]["features"]))
        summary += "\n---------------------" 
        for zone in self.ZONES:
            summary += "\n Zone %d features: %s" % (zone, str(sorted(self.ZONES[zone]["features"])).replace('L',''))
        print summary
        QMessageBox.information(self.iface.mainWindow(),"EquiCluster", summary)
            

    def run(self):
        """Run method that performs all the real work"""

        ##############################################
        def check_module():
            ## Check if module required exists 
            try:
                __import__("pygraph")
            except ImportError:
                msg = "ERROR: [pygraph] not found!!\n"
                msg += "Please, install pygraph in QGis python and restart QGis"
                QMessageBox.information(self.iface.mainWindow(),"EquiCluster", msg)
                return False
            else:
                return True
        
        import sys, os
        #print "OLD PATH:"
        #print sys.path
        
        current_path = os.path.dirname(os.path.abspath(__file__))
        if not current_path in sys.path:
            sys.path.append(current_path)
        
        is_import_correct = check_module()
        
        #print "NEW PATH:"
        #print sys.path
        
        if not is_import_correct:
            return
        ##############################################

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
