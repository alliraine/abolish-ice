from fastapi import FastAPI, Query
from pydantic import BaseModel
import pandas as pd
import geopy.distance
import pgeocode
from geopy.geocoders import Nominatim

app = FastAPI()

# Load your dataset
df_part = pd.read_csv("data/participating_prev.csv")
df_pend = pd.read_csv("data/pending_prev.csv")
df_all = pd.concat([df_part, df_pend], ignore_index=True)

# Ensure consistent casing
df_all.columns = [col.upper() for col in df_all.columns]

# Add geocoded location (this can be cached)
nomi = pgeocode.Nominatim('us')
geolocator = Nominatim(user_agent="abolish-ice-api")
df_all['LOCATION'] = df_all['STATE'] + ' ' + df_all['COUNTY']

def geocode_agency(row):
    query = f"{row['LAW ENFORCEMENT AGENCY']}, {row['STATE']}"
    location = nomi.query_postal_code(query)
    if pd.isna(location.latitude) or pd.isna(location.longitude):
        return pd.Series([None, None])
    else:
        return pd.Series([location.latitude, location.longitude])

# Geocode each agency using LAW ENFORCEMENT AGENCY and STATE
df_all[['AGENCY_LAT', 'AGENCY_LON']] = df_all.apply(geocode_agency, axis=1)

@app.get("/agencies/nearby")
def get_agencies(zipcode: str = Query(None), city: str = Query(None), state: str = Query(None)):
    if zipcode:
        center = nomi.query_postal_code(zipcode)
        if pd.isna(center.latitude) or pd.isna(center.longitude):
            return {"error": "Location could not be resolved."}
        center_lat = center.latitude
        center_lon = center.longitude
    elif city and state:
        location = geolocator.geocode(f"{city}, {state}")
        if location is None:
            return {"error": "Location could not be resolved."}
        center_lat = location.latitude
        center_lon = location.longitude
    else:
        return {"error": "Please provide either a zipcode or city and state"}

    def within_radius(row):
        if pd.isna(row['AGENCY_LAT']) or pd.isna(row['AGENCY_LON']):
            return False
        dist = geopy.distance.distance(
            (center_lat, center_lon),
            (row['AGENCY_LAT'], row['AGENCY_LON'])
        ).miles
        return dist <= 35

    matches = df_all[df_all.apply(within_radius, axis=1)]

    return matches[['LAW ENFORCEMENT AGENCY', 'STATE', 'SUPPORT TYPE']].to_dict(orient='records')


# Run the server if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)