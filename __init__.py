# -*- coding: utf-8 -*-
"""
/***************************************************************************
 isozonification
                                 A QGIS plugin
 Divide in zones/clusters of polygons using an attrinbute
                             -------------------
        begin                : 2015-06-08
        copyright            : (C) 2015 by Nacho Varela
        email                : nachouve@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load isozonification class from file isozonification.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .isozonification import isozonification
    return isozonification(iface)
