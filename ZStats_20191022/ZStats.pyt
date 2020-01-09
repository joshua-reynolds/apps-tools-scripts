import os
import time
import shutil
import arcpy
from arcpy.sa import *
import pandas as pd
from pandas import DataFrame
import getpass


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "Zonal Stats Tool"
		self.alias = "ZonalStatsTool"

		# List of tool classes associated with this toolbox
		self.tools = [ZonalStats]


class ZonalStats(object):
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Multi-Variate Zonal Statistics as Table"
		self.description = "Summarizes the values of a raster(s) within the zones of a feature layer and reports the results to a table. Must be run through ArcPro, requires dbfread python package install."
		self.canRunInBackground = False

	def getParameterInfo(self):
		"""Define parameter definitions"""

		# 1st parameter
		param0 = arcpy.Parameter(
		    displayName="Input Zone Features",
		    name="in_zone_features",
		    datatype="GPFeatureLayer",
		    parameterType="Required",
		    direction="Input")

		# 2nd parameter
		param1 = arcpy.Parameter(
		    displayName="Unique ID Field",
		    name="unique_id_field",
		    datatype="Field",
		    parameterType="Required",
		    direction="Input")

		param1.parameterDependencies = [param0.name]

		# 3rd parameter
		param2 = arcpy.Parameter(
		    displayName="Raster Directory",
		    name="raster_directory",
		    datatype="DEFolder",
		    parameterType="Required",
		    direction="Input")

		# 4th parameter
		param3 = arcpy.Parameter(
		    displayName="Statistics Type",
		    name="statistics_type",
		    datatype="GPString",
		    parameterType="Optional",
		    direction="Input")

		param3.filter.type = "ValueList"
		param3.filter.list = ["ALL", "MEAN_STD"]
		param3.value = "ALL"

		# 5th parameter
		param4 = arcpy.Parameter(
		    displayName="Keep Zones With No Data Pixels",
		    name="keep_zones_with_no_data",
		    datatype="GPString",
		    parameterType="Optional",
		    direction="Input")

		param4.filter.type = "ValueList"
		param4.filter.list = ["KEEP", "DISCARD"]
		param4.value = "KEEP"

		# 6th parameter
		param5 = arcpy.Parameter(
		    displayName="Convert Float Rasters to Integer (Optional)",
		    name="convert_float_to_int",
		    datatype="GPString",
		    parameterType="Optional",
		    direction="Input")

		param5.filter.type = "ValueList"
		param5.filter.list = ["CONVERT", "DON'T CONVERT"]
		param5.value = "CONVERT"

		# 7th parameter
		param6 = arcpy.Parameter(
		    displayName="Raster Conversion Scale Value (Optional)",
		    name="conversion_scale_value",
		    datatype="GPString",
		    parameterType="Optional",
		    direction="Input")

		param6.filter.type = "ValueList"
		param6.filter.list = ["10", "100", "1000"]
		param6.value = "100"

		# 8th parameter
		param7 = arcpy.Parameter(
		    displayName="Output Table",
		    name="output_table",
		    datatype="DEFile",
		    parameterType="Required",
		    direction="Output")
		param7.filter.list = ["csv"]

		params = [param0, param1, param2, param3, param4, param5, param6, param7]
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""
		return

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
		parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""

		#========================
		# USER ARGS
		#========================

		zones = parameters[0].valueAsText
		unique_field = parameters[1].valueAsText
		raster_path = parameters[2].valueAsText
		stats = parameters[3].valueAsText
		keep_zones_with_no_data = parameters[4].valueAsText
		integerize_floats = parameters[5].valueAsText
		scale_factor = int(parameters[6].valueAsText)
		out_csv = parameters[7].valueAsText
		out_path = os.path.dirname(out_csv)

		#========================
		# RUN ZONAL STATS
		#========================

		# Set the no data parameter
		if keep_zones_with_no_data == 'KEEP': no_data_param = 'DATA'
		else: no_data_param = 'NODATA'

		# Set the integerize floats parameter
		if integerize_floats == 'CONVERT': integerize_floats_param = True
		else: integerize_floats_param = False

		# Create temp processing directory
		temp_dir = os.path.join(out_path, 'temp_zstat_{}'.format(time.strftime('%Y%m%d_%H%M%S',time.localtime())))
		if not os.path.exists(temp_dir):
			os.makedirs(temp_dir)

		arcpy.AddMessage("Running Zonal Stats on {} segments...".format(arcpy.GetCount_management(zones)))
		arcpy.env.overwriteOutput = True

		# Get list of rasters to obtain stats for
		arcpy.env.workspace = raster_path
		rasters = arcpy.ListRasters()
		out_dbfs = []

		for raster in rasters:

			# Get some raster metadata
			raster_describe_obj = arcpy.Describe(raster)
			number_of_bands = raster_describe_obj.bandCount
			band_prefix = raster_describe_obj.children[0].name.split("_")[0]

			out_raster_name = raster.split(".")[0]
			arcpy.AddMessage("Working on {} ({} bands)...\n".format(raster, number_of_bands))

			if number_of_bands > 1:
				for band in range(1, number_of_bands + 1):

					# Get the band as a raster object
					raster_band = arcpy.Raster(os.path.join(raster, "{0}_{1}".format(band_prefix, band)))

					# Get the band data type
					band_data_type = str(arcpy.Describe(raster_band).pixelType)

					# Form the output table name
					out_table_name = os.path.join(temp_dir, "{0}_band_{1}.dbf".format(out_raster_name, band))
					out_dbfs.append(out_table_name)

					# Convert float to int, if conditions are met
					if band_data_type in ['F32', 'F64'] and integerize_floats_param == True:

						arcpy.AddMessage('Converting Float Raster to Integer...')
						converted_raster_band = Int(Times(raster_band, scale_factor))

						# Run zonal stats
						ZonalStatisticsAsTable(zones, unique_field, converted_raster_band, out_table_name, no_data_param, stats)
						#arcpy.DeleteFeatures_management(converted_raster_band)

					else:
						# Run zonal stats
						ZonalStatisticsAsTable(zones, unique_field, raster_band, out_table_name, no_data_param, stats)
			else:
				# Get the raster data type
				raster_data_type = str(arcpy.Describe(raster).pixelType)

				# Form the output table name
				out_table_name = os.path.join(temp_dir, "{0}.dbf".format(out_raster_name))
				out_dbfs.append(out_table_name)

				# Convert float to int, if conditions are met
				if raster_data_type in ['F32', 'F64'] and integerize_floats_param == True:
					print('Converting Float Raster to Int...')
					converted_raster = Int(Times(raster, scale_factor))

					# Run zonal stats
					ZonalStatisticsAsTable(zones, unique_field, converted_raster, out_table_name, no_data_param, stats)
					#arcpy.DeleteFeatures_management(converted_raster)

				else:
					# Run zonal stats
					ZonalStatisticsAsTable(zones, unique_field, raster, out_table_name, no_data_param, stats)


		arcpy.AddMessage("Zonal Stats calculation finished...")

		#========================
		# MERGE TABLES
		#========================

		# Create empty master dataframe
		arcpy.AddMessage("Merging Tables...")
		ZonalStats = pd.DataFrame()

		# Loop through stored dbf paths
		for dbf in out_dbfs:

			# Convert dbf to csv - Pandas can't read dbf
			csv = dbf.replace(".dbf", ".csv")
			arcpy.TableToTable_conversion(dbf, temp_dir, os.path.basename(csv))

			# Read created csv into pandas as dataframe
			temp_frame = pd.read_csv(csv)

			# Drop OID_ and ZONE_CODE fields from temporary dataframe if they exist
			if 'OID_' in list(temp_frame.columns):
				temp_frame = temp_frame.drop(columns='OID_')

			if 'ZONE_CODE' in list(temp_frame.columns):
				temp_frame = temp_frame.drop(columns='ZONE_CODE')

			# Get column names
			column_names = list(temp_frame.columns)

			# Get the basename of the csv for column naming
			fileName = os.path.basename(dbf).split('.')[0]
			arcpy.AddMessage("Merging table created from {}...\n".format(fileName))

			# Create empty list for new column names
			new_column_names = []

			# Populate new list of column names
			new_column_names.append(column_names[0].upper())

			# Skip join field name and append new column names to list
			for name in column_names[1:]:

				# Shorten field names
				if name == 'COUNT': name = 'CNT'
				elif name == 'RANGE' : name = 'RNG'
				elif name == 'VARIETY': name = 'VAR'
				elif name == 'MAJORITY': name = 'MAJ'
				elif name == 'MINORITY': name = 'MIN'
				elif name == 'MEDIAN': name = 'MED'

				new_column_names.append(name + '_' + fileName.upper())

			# Apply new column names to temp dataframe
			temp_frame.columns = new_column_names

			# If the main table is empty, make the current table the main, otherwise merge current table to main by unique field
			if ZonalStats.empty == True:
				ZonalStats = temp_frame
			else:
				ZonalStats = ZonalStats.merge(temp_frame, left_on = unique_field, right_on = unique_field, how = 'inner')


		arcpy.AddMessage("Tables merged!")
		ZonalStats.to_csv(out_csv, index=False) 

		#=====================================
		# Clean-up
		#====================================

		# Delete temporary working directory
		try: shutil.rmtree(temp_dir)
		except: arcpy.AddWarning("Warning: Script was successful. However, some temporary files may not have been removed.")

		# Easter Egg
		if  getpass.getuser() == "gabrielbellante":
			try:
				import ctypes
				ctypes.windll.user32.SystemParametersInfoW(20, 0, r"C:\Windows\WinSxS\amd64_microsoft-windows-h..phicfirstrun.assets_31bf3856ad364e35_10.0.17134.1_none_50a5acde7a623f1c\Background_ForwardDirection_RoomScale.jpg" , 0)
			except:pass

