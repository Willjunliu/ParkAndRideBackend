from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
import asyncio
import os
import time
from fastapi.middleware.cors import CORSMiddleware

apikey = os.getenv("API_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(updater())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

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

async def fetch_parks():
    results = {}

    async with httpx.AsyncClient(timeout=15) as client:
        facilities_res = await client.get(url, headers=headers)
        facilities = facilities_res.json()

        for facility_id, facility_name in facilities.items():
            if "historical only" in facility_name.lower():
                continue

            try:
                res = await client.get(
                    url,
                    headers=headers,
                    params={"facility": facility_id}
                )
                data = res.json()

                total = int(data["spots"])
                occupied = int(data["occupancy"]["total"])

                results[facility_id] = {
                    "name": facility_name,
                    "free": total - occupied,
                    "total": total,
                    "occupied": occupied,
                    "last_updated": data["MessageDate"]
                }

            except Exception:
                continue

    return results

async def updater():
    global CACHE, LAST_UPDATED

    while True:
        try:
            print("Updating cache...")
            new_data = await fetch_parks()

            if new_data:
                CACHE = new_data
                LAST_UPDATED = time.time()
                print("Cache updated")

        except Exception as e:
            print("Updater error:", e)

        await asyncio.sleep(CACHE_SECONDS)


@app.get("/parks")
def get_parks():
    return {
        "last_updated": LAST_UPDATED,
        "data": CACHE
    }