# NYC_Taxi_trips
Full-Stack system data analytics for NYC Taxi trips with data cleaning pipeline, custom algorithms, REST API, caching, and visualization dashboard.

## Project Stucture
```
NYC_Taxi_trips/
│
├── data_pipeline/                
│   ├── load_raw_data.py
│   ├── clean_trips.py
│   ├── feature_engineering.py
│   ├── excluded_records.py
│   ├── run_pipeline.py
│
├── data/                         
│   ├── raw/                       
│   ├── parquet/                   
│   ├── geojson/                  
│   ├── taxi_zones/                
│   │   ├── taxi_zones.dbf
│   │   ├── taxi_zones.prj
│   │   ├── taxi_zones.sbn
│   │   ├── taxi_zones.sbx
│   │   ├── taxi_zones.shp
│   │   ├── taxi_zones.shp.xml
│   │   └── taxi_zones.shx
│   └── cleaned_data/              
│
├── docs/                          
│   ├── pipeline/                  
│   │   ├── download_raw_and_cleaned-data.md  
│   │   ├── Option_A.png                         
│   │   └── Pipeline_guide.md                    
│
├── convert_csv_to_parquet.py      
├── convert_shp_to_geojson.py      
├── requirements.txt               
├── .gitignore                     
├── README.md                      
│
├── backend/                      
├── frontend/                      

```

## Simplified system Architecure
**System Architecture Link**: (https://drive.google.com/file/d/1paM_y9yGavcYh1p_ihe1HPoM7qEZtic9/view?usp=sharing)