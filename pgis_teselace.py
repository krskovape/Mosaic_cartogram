from arcpy import *
from math import inf, ceil
import sys
import os

# set workspace
path = os.getcwd()
env.workspace = path
env.overwriteOutput = 1

def tesselation(input_polygon, shape, area, spatial_ref):
    # create tesselation grid
    GenerateTessellation_management("temp_tess.shp", input_polygon, shape, area, spatial_ref)

    # select tiles intersecting the input polygon
    MakeFeatureLayer_management("temp_tess.shp", "tess_lyr")
    SelectLayerByLocation_management("tess_lyr", "INTERSECT", input_polygon, selection_type = "NEW_SELECTION")
    CopyFeatures_management("tess_lyr", "tess_pol.shp")
    Delete_management("tess_lyr")

    # get number of tiles
    r = GetCount_management("tess_pol.shp")
    count = int(r[0])

    return count

# parameters for input and output polygon, shape of tiles and its number 
input_polygon = sys.argv[1]
output = sys.argv[2]
shape = sys.argv[3]
number = int(sys.argv[4])

# get spatial reference of input polygon
spatial_ref = Describe(input_polygon).spatialReference

# get area of the input polygon
CalculateGeometryAttributes_management(input_polygon, [["Area_pol", "AREA"]], area_unit="SQUARE_KILOMETERS")
sc = SearchCursor(input_polygon)
row = next(sc)
area_pol = row.getValue("Area_pol")

# get area of one tile
area_tile = area_pol / number
area = f"{area_tile} SquareKilometers"

# create initial tesselation
count = tesselation(input_polygon, shape, area, spatial_ref)

i = 0
min_k = inf
min_area = 0

while count != number:
    # end after 20 iterations
    if i == 20:
        break

    # difference between given and created number of tiles, how much should be changed the area of one tile
    k = count - number
    a = (abs(k) * area_tile) / number

    # created more tiles than given number, enlarge the area of one tile
    if k > 0:
        # update minimum difference between number of tiles
        if k < min_k:
            min_k = k
            min_area = area_tile

        area_tile += a

    # created less tiles than given number, reduce the area of one tile
    elif k < 0:
        area_tile -= a

    # create tesselation with updated tile area
    area = f"{area_tile} SquareKilometers"
    count = tesselation(input_polygon, shape, area, spatial_ref)

    i += 1

# delete tiles to get the given number of them
if count != number:
   # create tesselation with minimal tile redundancy
    area = f"{min_area} SquareKilometers"
    count = tesselation(input_polygon, shape, area, spatial_ref)

    # copy tesselation into new feature class
    CopyFeatures_management("tess_pol.shp", "tess_final.shp")
    MakeFeatureLayer_management("tess_final.shp", "tess_lyr")

    # get number of created tiles
    r = GetCount_management("tess_lyr")
    length = int(r[0])

    # get number of tiles to be deleted from start and end
    if min_k % 2 == 0:
        s = min_k / 2
        e = min_k - s
    else:
        s = ceil(min_k / 2)
        e = min_k - s
    
    # list for IDs of the tiles to be deleted
    id_list = []

    # IDs of tiles to be deleted from the beginning 
    for i in range(s):
        id_list.append(i)
    
    # IDs of tiles to be deleted from the end 
    for i in range(length - e, length):
        id_list.append(i)
    
    # select tiles with given ID
    qry = '"FID" IN ({0})'.format(', '.join(map(str, id_list)) or 'NULL')
    SelectLayerByAttribute_management("tess_lyr", where_clause= qry)

    # delete selected tiles
    DeleteFeatures_management("tess_lyr")
    Delete_management("tess_lyr")

    # save final tesselation to output file
    CopyFeatures_management("tess_final.shp", output)

else:
    # save final tesselation to output file
    CopyFeatures_management("tess_pol.shp", output)

# clean
Delete_management("temp_tess.shp")
Delete_management("tess_final.shp")
Delete_management("tess_pol.shp")

# c:\Progra~1\ArcGIS\Pro\bin\Python\scripts\propy.bat pgis_teselace.py Cesko_polygon.shp vystup.shp HEXAGON 500