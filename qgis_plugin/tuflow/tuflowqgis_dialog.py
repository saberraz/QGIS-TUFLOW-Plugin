# -*- coding: utf-8 -*-
"""
/***************************************************************************
 tuflowqgis_menuDialog
                                 A QGIS plugin
 Initialises the TUFLOW menu system
                             -------------------
        begin                : 2013-08-27
        copyright            : (C) 2013 by Phillip Ryan
        email                : support@tuflow.com
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

#import csv
import os.path
import operator
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import glob
from tuflowqgis_library import *

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")


# ----------------------------------------------------------
#    tuflowqgis increment selected layer
# ----------------------------------------------------------

from ui_tuflowqgis_increment import *

class tuflowqgis_increment_dialog(QDialog, Ui_tuflowqgis_increment):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		fpath = None
		
		if cLayer:
			cName = cLayer.name()
			dp = cLayer.dataProvider()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (fpath):
			self.outfolder.setText(fpath)
			self.outfilename.setText(fpath + "/"+fname)
		else:
			self.outfolder.setText('No layer currently open!')
			self.outfilename.setText('No layer currently open!')

        def browse_outfile(self):
		newname = QFileDialog.getSaveFileName(None, "Output Shapefile", 
			self.outfilename.displayText(), "*.shp")
                if newname != None:
                	self.outfilename.setText(newname)


	def run(self):
		if self.checkBox.isChecked():
			keepform = True
		else:
			keepform = False
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		savename = unicode(self.outfilename.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"Info", savename )
		message = tuflowqgis_duplicate_file(self.iface, layer, savename, keepform)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")

# ----------------------------------------------------------
#    tuflowqgis create tuflow directory structure
# ----------------------------------------------------------
from ui_tuflowqgis_create_tf_dir import *		
class tuflowqgis_create_tf_dir_dialog(QDialog, Ui_tuflowqgis_create_tf_dir):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		message, tffolder, tfexe, tf_prj = load_project(project)
		if message != None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		self.outdir.setText(tffolder)
		self.TUFLOW_exe.setText(tfexe)
		self.sourceCRS.setText(tf_prj)
		try:
			self.exefolder = os.path.dirname(tfexe)
		except:
			self.exefolder = ''
		
		i = 0
		if tf_prj != "Undefined":
			self.sourcelayer.addItem("Use saved projection")
			cLayer = False
			self.sourcelayer.setCurrentIndex(0)
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cLayer.name():
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection. \nPlease open or create a file in the desired projection.")
			
			#else:
			#	QMessageBox.warning(self.iface.mainWindow(), "Setting Projection", "No layer selected, a shapefile is required for setting the model projection.")
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

	def browse_outdir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			self.outdir.setText(newname)
	
	def browse_exe(self):
	
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exefolder, "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.exe = inFileName
		self.settings.setValue("TUFLOW_Create_Dir/exe", inFileName)
		self.TUFLOW_exe.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Create_Dir/exeDir", head)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		layer = tuflowqgis_find_layer(layername)
		crs = layer.crs()
		crs_id = crs.authid()
		crs_prj = crs.toProj4()
		self.sourceCRS.setText(crs_prj)
	def run(self):
		layername = unicode(self.sourcelayer.currentText())
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		tf_prj = unicode(self.sourceCRS.displayText()).strip()
		if layername == "Use saved projection":
			crs = QgsCoordinateReferenceSystem()
			crs.createFromProj4(tf_prj)
		else:
			layer = tuflowqgis_find_layer(layername)
			crs = layer.crs()

		
		QMessageBox.information( self.iface.mainWindow(),"Creating TUFLOW directory", basedir)
		
		message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory", message)
		if (self.checkBox.isChecked()):
			tcf = os.path.join(basedir+"\\TUFLOW\\runs\\Create_Empties.tcf")
			message = run_tuflow(self.iface, tfexe, tcf)
			if message <> None:
				QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW", message)
# ----------------------------------------------------------
#    tuflowqgis import empty tuflow files
# ----------------------------------------------------------
from ui_tuflowqgis_import_empties import *
class tuflowqgis_import_empty_tf_dialog(QDialog, Ui_tuflowqgis_import_empty):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)

		message, tffolder, tfexe, tf_prj = load_project(project)
		if message != None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		
		QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		self.emptydir.setText(tffolder+"\\TUFLOW\\model\\gis\\empty")

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			self.emptydir.setText(newname)


	def run(self):
		runID = unicode(self.txtRunID.displayText()).strip()
		basedir = unicode(self.emptydir.displayText()).strip()

		# Compile a list and header of selected attributes
		empty_types = []
		for x in range(0, self.emptyType.count()):
			list_item = self.emptyType.item(x)
			if list_item.isSelected():
				empty_types.append(list_item.text())

		# check which geometries are selected
		points = self.checkPoint.isChecked()
		lines = self.checkLine.isChecked()
		regions = self.checkRegion.isChecked()

		# run create dir script
		message = tuflowqgis_import_empty_tf(self.iface, basedir, runID, empty_types, points, lines, regions)
		#message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)

# ----------------------------------------------------------
#    tuflowqgis Run TUFLOW (Simple)
# ----------------------------------------------------------
from ui_tuflowqgis_run_tf_simple import *
class tuflowqgis_run_tf_simple_dialog(QDialog, Ui_tuflowqgis_run_tf_simple):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)

		# load settting from project file
		message, tffolder, tfexe, tf_prj = load_project(project)
		self.runfolder = tffolder+"\\TUFLOW\\runs\\"
		self.exefolder = os.path.dirname(tfexe)
		if message != None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		self.TUFLOW_exe.setText(tfexe)
		
		QObject.connect(self.browsetcffile, SIGNAL("clicked()"), self.browse_tcf)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		files = glob.glob(unicode(tffolder)+"\\TUFLOW\\runs\\*.tcf")
		self.tcfin=''
		if (len(files) > 0):
			files.sort(key=os.path.getmtime, reverse=True)
			self.tcfin = files[0]
		if (len(self.tcfin)>3):
			self.tcf.setText(self.tcfin)
		# open settings for previous instances
		#self.settings = QSettings()
		#self.exe = str(self.settings.value("TUFLOW_Run_TUFLOW/exe", os.sep).toString())
		#self.exe_dir = str(self.settings.value("TUFLOW_Run_TUFLOW/exeDir", os.sep).toString())
		#self.tcfin = str(self.settings.value("TUFLOW_Run_TUFLOW/tcf", os.sep).toString())
		#self.tcfdir = str(self.settings.value("TUFLOW_Run_TUFLOW/tcfDir", os.sep).toString())
		

		
		#if (len(self.exe)>3): # use last folder if stored
		#	self.TUFLOW_exe.setText(self.exe)

	def browse_tcf(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW Control File', self.runfolder, "TUFLOW Control File (*.tcf)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.tcfin = inFileName
		self.settings.setValue("TUFLOW_Run_TUFLOW/tcf", inFileName)
		self.tcf.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Run_TUFLOW/tcfDir", head)

	def browse_exe(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exefolder, "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.exe = inFileName
		self.settings.setValue("TUFLOW_Run_TUFLOW/exe", inFileName)
		self.TUFLOW_exe.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Run_TUFLOW/exeDir", head)

	def run(self):
		tcf = unicode(self.tcf.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		QMessageBox.information(self.iface.mainWindow(), "Running TUFLOW","Starting simulation: "+tcf+"\n Executable: "+tfexe)
		message = run_tuflow(self.iface, tfexe, tcf)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW", message)

# ----------------------------------------------------------
#    tuflowqgis points to lines
# ----------------------------------------------------------
from ui_tuflowqgis_line_from_points import *

class tuflowqgis_line_from_points(QDialog, Ui_tuflowqgis_line_from_point):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		fpath = None
		cName = ''
		
		if cLayer:
			cName = cLayer.name()
			dp = cLayer.dataProvider()
			datacolumns = dp.fields()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate columns layers")
			fields = cLayer.pendingFields()
			for (counter, field) in enumerate(fields):
				self.elev_attr.addItem(str(field.name()))
				if str(field.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(counter)
				elif str(field.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(counter)
			# below is for QGIS 1.8
			#for key,value in datacolumns.items():
			#	#print str(key) + " = " + str(value.name())
			#	self.elev_attr.addItem(str(value.name()))
			#	if str(value.name()).lower() == 'z':
			#		self.elev_attr.setCurrentIndex(key)
			#	elif str(value.name()).lower() == 'elevation':
			#		self.elev_attr.setCurrentIndex(key)

		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate source layers")
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate source layers")
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (i == 0):
			self.outfolder.setText(fpath)
			self.outfilename.setText(fpath + "/"+fname)

		# Connect signals and slots
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.source_changed) 
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)


	def browse_outfile(self):
		newname = QFileDialog.getSaveFileName(None, "Output Shapefile", 
			self.outfilename.displayText(), "*.shp")
                if newname != None:
                	self.outfilename.setText(newname)

	def source_changed(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Source Changed")
		layername = unicode(self.sourcelayer.currentText())
		self.cLayer = tuflowqgis_find_layer(layername)
		self.elev_attr.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", self.cLayer.name())
			datacolumns = self.cLayer.dataProvider().fields()
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Point geometry layer")
			else:
				QMessageBox.information(self.iface.mainWindow(), "Info", "Please select point layer type")
			fields = self.cLayer.pendingFields()
			for (counter, field) in enumerate(fields):
				self.elev_attr.addItem(str(field.name()))
				if str(field.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(counter)
				elif str(field.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(counter)
			

	def run(self):
		import math
		layername = unicode(self.sourcelayer.currentText())
		self.layer = tuflowqgis_find_layer(layername)
		savename = unicode(self.outfilename.displayText()).strip()
		z_col = self.elev_attr.currentIndex()
		dmax_str = unicode(self.dmax.displayText())
		try:
			dmax = float(dmax_str)
		except:
			QMessageBox.criticl( self.iface.mainWindow(),"Error", "Error converting input distance to numeric data type.  Make sure a number is specified." )
		QMessageBox.information( self.iface.mainWindow(),"debug", "starting" )
		
		npt = 0
		x = []
		y = []
		z = []
		feature = QgsFeature()
		self.layer.dataProvider().select(self.layer.dataProvider().attributeIndexes())
		self.layer.dataProvider().rewind()
		feature_count = self.layer.dataProvider().featureCount()
		QMessageBox.information(self.iface.mainWindow(),"debug", "count = "+str(feature_count))
		while self.layer.dataProvider().nextFeature(feature):
			npt = npt + 1
			geom = feature.geometry()
			xn = geom.asPoint().x()
			yn = geom.asPoint().y()
			x.append(xn)
			y.append(yn)
			zn = feature.attributeMap()[z_col].toString()
			if npt == 1:
				QMessageBox.information(self.iface.mainWindow(),"debug", "x = "+str(xn)+", y = "+str(yn))
				QMessageBox.information(self.iface.mainWindow(),"debug", "z = "+zn)
			z.append(float(zn))
		QMessageBox.information(self.iface.mainWindow(),"debug", "finished reading points")	
		QMessageBox.information(self.iface.mainWindow(),"debug", "npts read = "+str(npt))
		
		# Create output file
		v_layer = QgsVectorLayer("LineString", "line", "memory")
		pr = v_layer.dataProvider()
		
		# add fields
		fields = { 0 : QgsField("z", QVariant.Double),1 : QgsField("dz", QVariant.Double),2 : QgsField("width", QVariant.Double),3 : QgsField("Options", QVariant.String) }
		#pr.addAttributes( [ QgsField("Z", QVariant.Double),
		#	QgsField("dz",  QVariant.Double),
		#	QgsField("width",  QVariant.Double),
		#	QgsField("Options", QVariant.String) ] )
					
		message = None
		if len(savename) <= 0:
			message = "Invalid output filename given"
		
		if QFile(savename).exists():
			if not QgsVectorFileWriter.deleteShapeFile(savename):
				message =  "Failure deleting existing shapefile: " + savename
	
		outfile = QgsVectorFileWriter(savename, "System", 
			fields, QGis.WKBLineString, self.layer.dataProvider().crs())
	
		if (outfile.hasError() != QgsVectorFileWriter.NoError):
			message = "Failure creating output shapefile: " + unicode(outfile.errorMessage())
		
		if message <> None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
			
		line_num = 0
		pt_num = 0
		pol = 0
		newline = True


		point_list = []
		for pt in range(npt):
			pt2x = x[pt]
			pt2y = y[pt]
			qpt = QgsPoint(pt2x,pt2y)
			#if pt <= 10:
			#	QMessageBox.information(self.iface.mainWindow(),"debug", "pt2x = "+str(pt2x)+", pt2y = "+str(pt2y))
			if newline:
				pt1x = pt2x
				pt1y = pt2y
				pol = 1
				newline = False
				
			else:
				dist = math.sqrt(((pt2x - pt1x)**2)+((pt2y - pt1y)**2))
				#if pt <= 10:
				#	QMessageBox.information(self.iface.mainWindow(),"debug", "dist = "+str(dist))
				if dist <= dmax: #part of same line
					point_list.append(qpt)
					pt1x = pt2x
					pt1y = pt2y
					pol = pol+1
				else:
					seg = QgsFeature()
					if point_list <> None and (pol > 2):
						seg.setGeometry(QgsGeometry.fromPolyline(point_list))
						outfile.addFeatures( [ seg ] )
						outfile.updateExtents()
					newline = True
					pt1x = pt2x
					pt1y = pt2y
					point_list = []
		del outfile
		#QgsMapLayerRegistry.instance().addMapLayers([v_layer])
		self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")
		#line_start = QgsPoint(x[0],y[0])
		#QMessageBox.information(self.iface.mainWindow(),"debug", "x1 = "+str(x[1])+", y0 = "+str(y[1]))
		#line_end = QgsPoint(x[1],y[1])
		#line = QgsGeometry.fromPolyline([line_start,line_end])
		# create a new memory layer
		#v_layer = QgsVectorLayer("LineString", "line", "memory")
		#pr = v_layer.dataProvider()
		# create a new feature
		#seg = QgsFeature()
		# add the geometry to the feature, 
		#seg.setGeometry(QgsGeometry.fromPolyline([line_start, line_end]))
		# ...it was here that you can add attributes, after having defined....
		# add the geometry to the layer
		#pr.addFeatures( [ seg ] )
		# update extent of the layer (not necessary)
		#v_layer.updateExtents()
		# show the line  
		#QgsMapLayerRegistry.instance().addMapLayers([v_layer])

# ----------------------------------------------------------
#    tuflowqgis configure tuflow project
# ----------------------------------------------------------
from ui_tuflowqgis_configure_tuflow_project import *		
class tuflowqgis_configure_tf_dialog(QDialog, Ui_tuflowqgis_configure_tf):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.project = project
		cLayer = self.canvas.currentLayer()
		fname = ''
		message, tffolder, tfexe, tf_prj = load_project(self.project)
		#dont give error here as it may be the first occurence
		#if message != None:
		#	QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		
		self.outdir.setText(tffolder)
		self.TUFLOW_exe.setText(tfexe)
		self.sourceCRS.setText(tf_prj)

		if tf_prj == "Undefined":
			if cLayer:
				cName = cLayer.name()
				crs = cLayer.crs()
				crs_id = crs.authid()
				crs_prj = crs.toProj4()
				self.sourceCRS.setText(crs_prj)

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		

		i = 0
		if tf_prj != "Undefined":
			self.sourcelayer.addItem("Use saved projection")
			cLayer = False
			self.sourcelayer.setCurrentIndex(0)
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cName:
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection. \nPlease open or create a file in the desired projection.")


	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			#self.outdir.setText(QString(newname))
			self.outdir.setText(newname)
	
	def browse_exe(self):
	
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', "", "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.TUFLOW_exe.setText(inFileName)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Use saved projection":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				crs = layer.crs()
				crs_id = crs.authid()
				crs_prj = crs.toProj4()
				self.sourceCRS.setText(crs_prj)
	def run(self):
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Saving TUFLOW configuration to project file")
		tf_prj = unicode(self.sourceCRS.displayText()).strip()
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		#writes
		try:
			self.project.writeEntry("configure_tuflow", "exe", tfexe)
			self.project.writeEntry("configure_tuflow", "folder", basedir)
			self.project.writeEntry("configure_tuflow", "projection", tf_prj)
			QMessageBox.information( self.iface.mainWindow(),"Configure TUFLOW project", "Settings saved successfully.")
		except:
			QMessageBox.information( self.iface.mainWindow(),"Configure TUFLOW project", "Error when writing to the project, ensure a project has been saved.")
# ----------------------------------------------------------
#    tuflowqgis splitMI into shapefiles
# ----------------------------------------------------------
from ui_tuflowqgis_splitMI import *
from splitMI_mod import *
class tuflowqgis_splitMI_dialog(QDialog, Ui_tuflowqgis_splitMI):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		cName = 'not defined'
		fpath = None
		
	#	if cLayer:
	#		cName = cLayer.name()
	#		dp = cLayer.dataProvider()
	#		ds = dp.dataSourceUri()
	#		try:
	#			fpath, fname = os.path.split(unicode(ds))
	#			ind = fname.find('|')
	#			if (ind>0):
	#				fname = fname[0:ind]
	#			fext, fname_noext, message = get_file_ext(fname)
	#		except:
	#			fpath = None
	#			fname = ''

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if cLayer == None:
			self.sourcelayer.setCurrentIndex(0)
		
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Undefined":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				dp = layer.dataProvider()
				ds = dp.dataSourceUri()
				try:
					fpath, fname = os.path.split(unicode(ds))
					ind = fname.find('|')
					if (ind>0):
						fname = fname[0:ind]
					fext, fname_noext, message = get_file_ext(fname)
				except:
					fpath = None
					fname = ''
				self.outfolder.setText(fpath)
				self.outprefix.setText(fname_noext)
		if (fpath):
			self.outfolder.setText(fpath)
			self.outprefix.setText(fname_noext)
		else:
			self.outfolder.setText('No layer currently open!')
			self.outprefix.setText('No layer currently open!')

	def browse_outdir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			self.outfolder.setText(newname)
	
	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Undefined":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				dp = layer.dataProvider()
				ds = dp.dataSourceUri()
				try:
					fpath, fname = os.path.split(unicode(ds))
					ind = fname.find('|')
					if (ind>0):
						fname = fname[0:ind]
					fext, fname_noext, message = get_file_ext(fname)
				except:
					fpath = None
					fname = ''
				self.outfolder.setText(fpath)
				self.outprefix.setText(fname_noext)
	def run(self):
		#QMessageBox.information( self.iface.mainWindow(),"debug", "run" )
		layername = unicode(self.sourcelayer.currentText())
		#QMessageBox.information( self.iface.mainWindow(),"debug", "layer name = :"+layername)
		layer = tuflowqgis_find_layer(layername)
		fext = "unknown"
		if layer != None:
			dp = layer.dataProvider()
			ds = unicode(dp.dataSourceUri())
			ind = ds.find('|')
			if (ind>0):
				fname = ds[0:ind]
			else:
				fname = ds
			fext, fname_noext, message = get_file_ext(fname)
		else:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "Layer name is blank, or unable to find layer")
		#QMessageBox.information( self.iface.mainWindow(),"debug", "file extension = :"+fext)
		outfolder = unicode(self.outfolder.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"debug", "folder = :"+outfolder)
		outprefix = unicode(self.outprefix.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"debug", "prefix = :"+outprefix)
		#message = tuflowqgis_duplicate_file(self.iface, layer, savename, keepform)
		message, ptshp, lnshp, rgshp, npt, nln, nrg = split_MI_util(self.iface, fname, outfolder, outprefix)
		
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Error Splitting file", message)
		#QMessageBox.information( self.iface.mainWindow(),"debug", ptshp)
		#QMessageBox.information( self.iface.mainWindow(),"debug", "npts: "+str(npt))
		QMessageBox.information( self.iface.mainWindow(),"debug", "Removing existing layer")
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		#self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")