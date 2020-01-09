# Author: Joshua Reynolds
# Last Updated: 6/18/2019

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import sys
gdal.UseExceptions()


"""
Wisdom from the school of Housman. When creating a raster, you first define the projection, then define the upper-left x and y, and the pixel size (aka the transform), then you add a matrix of values. EE will create an upper-left x and y for the exported raster that is relative to the specified origin
"""


#--------------------------------------------------------------
# functions to get the transform
#--------------------------------------------------------------

"""
adfGeoTransform[0] /* top left x */
    adfGeoTransform[1] /* w-e pixel resolution */
    adfGeoTransform[2] /* rotation, 0 if image is "north up" */
    adfGeoTransform[3] /* top left y */
    adfGeoTransform[4] /* rotation, 0 if image is "north up" */
    adfGeoTransform[5] /* n-s pixel resolution */ 
"""

# This function returns the transform of a raster
def get_transform(path):    
    raster = gdal.Open(path)
    gt = raster.GetGeoTransform()
    print('='*50 +'\nTransform\n' + '='*50)
    print(gt)
    print('\n')    
    return gt 

# This function returns the transform of a raster exactly how Google Earth Engine ingests it
def get_transform_for_gee(path):    
    raster = gdal.Open(path)
    gt = list(raster.GetGeoTransform())
    reordered_gt = [gt[1], gt[2], gt[0], gt[4], gt[5], gt[3]]
    print('='*50 +'\nTransform formatted for GEE\n' + '='*50)
    print(reordered_gt)
    print('\n')        
    return reordered_gt

#--------------------------------------------------------------
# get proj4 from shapefile prj file
#--------------------------------------------------------------

def esriprj2standards(shapeprj_path):
    prj_file = open(shapeprj_path, 'r')
    prj_txt = prj_file.read()
    srs = osr.SpatialReference()
    srs.ImportFromESRI([prj_txt])
    print 'Shape prj is: %s' % prj_txt
    print 'WKT is: %s' % srs.ExportToWkt()
    print 'Proj4 is: %s' % srs.ExportToProj4()
    srs.AutoIdentifyEPSG()
    print 'EPSG is: %s' % srs.GetAuthorityCode(None)

#--------------------------------------------------------------
# function to get the projection well-known text
#--------------------------------------------------------------

# This function returns the projection of a raster as well-known text
def get_projection_wkt(path):    
    raster = gdal.Open(path)
    proj = raster.GetProjection()
    print('='*50 +'\nProjection Well-Known Text\n' + '='*50)
    print(proj)
    print('\n')    
    return proj 

#--------------------------------------------------------------
# Convert WKT to Proj4
#--------------------------------------------------------------

def convert_wkt_to_proj4(wkt):
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    proj4 = srs.ExportToProj4()
    print('='*50 +'\nProj4\n' + '='*50)
    print(proj4)
    print('\n') 
    return proj4
    
    
#--------------------------------------------------------------
# MAIN
#--------------------------------------------------------------

if __name__ == "__main__":

    # Raster to get metadata for
    raster1 = r"\\166.2.126.77\tcc\TCC2016_CONUS\FINAL_TCC_IMAGES\Cartographic_NLCD\nlcd_2011_treecanopy_2019_08_31.img"
    wkt1 = get_projection_wkt(raster1)
    proj4_1 = convert_wkt_to_proj4(wkt1)
    transform1 = get_transform_for_gee(raster1)
    
    #raster2 = r"\\166.2.126.25\GTAC_Apps\Zonal_Stats_Testing\l8_fall_15m_pan_mosaic_pow_5m.img"
    #wkt2 = get_projection_wkt(raster2)
    #proj4_2 = convert_wkt_to_proj4(wkt2)
    #transform2 = get_transform_for_gee(raster2)
    
    #raster3 = r"E:\R10_Local\Raster_With_Lidar2\l8_fall_15m_pan_mosaic_pow_5m.img"
    #wkt3 = get_projection_wkt(raster3)
    #proj4_3 = convert_wkt_to_proj4(wkt3)
    #transform3 = get_transform_for_gee(raster3)
    
    print('\nDone!\n')
