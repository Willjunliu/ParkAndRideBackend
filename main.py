from fastapi import FastAPI
import requests
import os
import time
from fastapi.middleware.cors import CORSMiddleware

apikey = os.getenv("API_KEY")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing, allow all origins
    allow_methods=["*"],
    allow_headers=["*"],
)
url = "https://api.transport.nsw.gov.au/v1/carpark"
headers = {
    "Authorization": f"apikey {apikey}"
}

CACHE = {}
LAST_UPDATED = 0
CACHE_SECONDS = 60

@app.get("/test")
def test_key():
    return {"key_exists": apikey is not None}

def fetch_parks():
    response = requests.get(url, headers=headers)

    facilities = response.json()

    results = {}

    for facility_id, facility_name in facilities.items():
        try:
            response = requests.get(
                url,
                headers=headers,
                params={"facility": facility_id},
                timeout=10
            )

            data = response.json()

            name = facility_name
            total_spaces = int(data["spots"])
            occupied_spaces = int(data["occupancy"]["total"])
            free_spaces = total_spaces - occupied_spaces

            if "historical only" in name.lower():
                continue
            results[facility_id] = {
                "name": name,
                "free": free_spaces,
                "total": total_spaces,
                "occupied": occupied_spaces,
                "last_updated": data["MessageDate"]
            }
        except Exception as e:
            continue
    return results 

@app.get("/parks")
def get_parks():
    global CACHE, LAST_UPDATED

    now = time.time()

    if now - LAST_UPDATED > CACHE_SECONDS:
        CACHE = fetch_parks()
        LAST_UPDATED = now

    return CACHE