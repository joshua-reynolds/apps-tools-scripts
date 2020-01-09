library(raster)
library(sp)
library(rgdal)
library(randomForest)
library(RStoolbox)
library(VSURF)
library(parallel)
library(snow)

# Set the seed
set.seed(33.259)

# Runtime tracking
start_time <- Sys.time()

# store ref points
points = readOGR(dsn = "", layer = "")

# Filter attributes to only the canopy cover field
points = points[, 2]


#----------------------------------------------
# BUILD SAMPLE DATA
#----------------------------------------------

ext = extent(raster(""))

# store predictor layers
mc = brick("")
mc = extend(crop(mc, ext), ext)

ndvi = raster("")
ndvi = extend(crop(ndvi, ext), ext)

ndmi = raster("")
ndmi = extend(crop(ndmi, ext), ext)

tcap = brick("")
tcap = dropLayer(tcap, c(4:6)) # Drop the noise bands
tcap = extend(crop(tcap, ext), ext)

pcomp = brick("")
pcomp = extend(crop(tcap, ext), ext)

ewmacd.ndvi = brick("")
ewmacd.ndvi = extend(crop(ewmacd.ndvi, ext), ext)

ewmacd.swir1 = brick("")
ewmacd.swir1 = extend(crop(ewmacd.swir1, ext), ext)

ewmacd.swir2 = brick("")
ewmacd.swir2 = extend(crop(ewmacd.swir2, ext), ext)

elev = raster("")
elev = extend(crop(elev, ext, snap='near'), ext)


# Stack the rasters for sampling and predicting later 
rasters = stack(mc, ndvi, ndmi, tcap, ewmacd.ndvi, ewmacd.swir1, ewmacd.swir2, elev)

#remove rasters from memory
rm(mc)
rm(ndmi)
rm(ndvi)
rm(tcap)
rm(ewmacd.ndvi)
rm(ewmacd.swir1)
rm(ewmacd.swir2)
rm(elev)


# Extract rasters values to points - takes about 20-30 minutes
points.extract = data.frame(extract(rasters, points, sp=T))

# Drop XY coordinate and optional fields
points.extract2 = points.extract[, -c((length(points.extract)-2):length(points.extract))]

# Drop points with no data
points.extract3 = na.omit(points.extract2)

# Remove duplicates
points.extract5 = unique(points.extract3)


# Format the X and Y variables
x = points.extract5[,2:length(points.extract5[1,])]
y = as.numeric(as.character(points.extract5[,1]))


#----------------------------------------------
# VSURF
#----------------------------------------------

# Variable Selection using VSURF - takes about 40 min
tcc_vsurf = VSURF(x, y, ntree=500,  parallel = TRUE, ncores=detectCores() - 1)
print(tcc_vsurf$varselect.pred)

newX.pred = x[tcc_vsurf$varselect.pred]
rasters.pred = subset(rasters, tcc_vsurf$varselect.pred)


#----------------------------------------------
# RANDOM FOREST MODELING
#----------------------------------------------


# Create RF Model and print the results
RF_3030_surface_reflectance = tuneRF(x=newX.pred, y=y, ntreeTry = 50, importance=TRUE, doBest=TRUE, plot=FALSE)
print(RF_3030_surface_reflectance)
varImpPlot(RF_3030_surface_reflectance, type =1)


#----------------------------------------------
# PREDICTION
#----------------------------------------------

# predict function
PredictFunction <- function(RF_3030_surface_reflectance, data)
{
  predictedValue = predict(RF_3030_surface_reflectance , data, predict.all = T)
  predictedValue_tcc_se = sqrt(apply(predictedValue$individual,1,FUN = var))
  temp = data.frame(predictedValue$aggregate)
  temp$se = predictedValue_tcc_se
  return(temp)
}

# Predict TCC and SE to raster
time1 = Sys.time()
beginCluster()
cl = getCluster()
clusterEvalQ(cl,rasterOptions(chunksize = 1e+06))
predictedValue = clusterR(rasters, predict, args = list(model = RF_3030_surface_reflectance, fun=PredictFunction, index = 1:2))
endCluster()
time2 = Sys.time()
totaltime = time2 - time1
print(totaltime)
rm(cl)
gc()


#==================================
# EXPORTS
#==================================

# Get the date
date = format(Sys.Date(), format="%Y%m%d")

# Write raster to working directory
rasterPath = paste('', date, '.img', sep = "")
writeRaster(predictedValue, filename = rasterPath , datatype = "FLT4S", overwrite=T)

# Runtime tracking
end_time <- Sys.time()
paste('Process took: ', end_time - start_time, sep=' ')

# export vsurf training data
y.df = data.frame(y)
colnames(y.df) = ""
table4export = cbind(y.df, newX.pred)
training_pts_path = paste('', date, '.txt', sep = "")
write.table(table4export, training_pts_path)

# save rdata
rdata_path =paste('', date, '.RData', sep = "")
save(RF_3030_surface_reflectance, table4export, points.extract5, tcc_vsurf, x, y,file=rdata_path)


