import arcpy
from arcpy.sa import *
import os
import shutil
import time
import pandas as pd
from pandas import DataFrame
import getpass


#========================
# USER ARGS
#========================

zones = r"F:\zonalstats\NRIS_Poly_Filtered.shp"
unique_field = 'SPATIAL_ID'
raster_path = r'F:\zonalstats'
stats = "ALL"
out_csv = 'F:\zonalstats\Result\out_zstat_{}.csv'.format(time.strftime('%Y%m%d_%H%M%S',time.localtime()))
temp_processing_path = r'C:\Temp'
ignore_no_data = True
integerize_floats = True
multiplier = 100

#========================
# RUN ZONAL STATS
#========================

# Set the no data parameter
if ignore_no_data == True: no_data_param = 'DATA'
else: no_data_param = 'NODATA'

# Create temp processing directory
temp_dir = os.path.join(temp_processing_path, 'tempZstat_{}'.format(time.strftime('%Y%m%d_%H%M%S',time.localtime())))
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
    
    # If raster is multiband
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
            if band_data_type in ['F32', 'F64'] and integerize_floats == True:
                
                arcpy.AddMessage('Converting Float Raster to Integer...')
                converted_raster_band = Int(Times(raster_band, multiplier))

                # Run zonal stats
                ZonalStatisticsAsTable(zones, unique_field, converted_raster_band, out_table_name, no_data_param, stats)
            
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
        if raster_data_type in ['F32', 'F64'] and integerize_floats == True:
            print('Converting Float Raster to Int...')
            converted_raster = Int(Times(raster, multiplier))
            
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

# Save merged data frame as csv
arcpy.AddMessage("Tables merged!")
ZonalStats.to_csv(out_csv, index=False) 
       
# Delete temporary working directory
try:shutil.rmtree(temp_dir)
except:arcpy.AddWarning("Warning: Script was successful. However, some temporary files may not have been removed.")

# Easter egg
if  getpass.getuser() == "gabrielbellante":
    try:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoW(20, 0, r"C:\Windows\WinSxS\amd64_microsoft-windows-h..phicfirstrun.assets_31bf3856ad364e35_10.0.17134.1_none_50a5acde7a623f1c\Background_ForwardDirection_RoomScale.jpg" , 0)
    except:pass

 

