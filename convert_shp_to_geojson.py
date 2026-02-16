import geopandas as gpd
from pathlib import Path

# Path to file
shapefile_path = "data/taxi_zones/taxi_zones.shp"
geojson_path = "data/geojson/taxi_zones.geojson"

#Load shapefile
gdf = gpd.read_file(shapefile_path)

# Save as GeoJSON
gdf.to_file(geojson_path, driver="GeoJSON")

print(f"** GEOJSON saved to {geojson_path} **")
