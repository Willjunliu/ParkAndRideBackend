from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
import asyncio
import os
import time
from fastapi.middleware.cors import CORSMiddleware

APIKEY = os.getenv("API_KEY")

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

URL = "https://api.transport.nsw.gov.au/v1/carpark"
HEADERS = {"Authorization": f"apikey {APIKEY}"}

CACHE = {}
LAST_UPDATED = 0
CACHE_SECONDS = 60

@app.get("/test")
def test_key():
    return {"key_exists": APIKEY is not None}

async def fetch_parks():
    results = {}

    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=15) as client:
        api_responce = await client.get(URL, headers=HEADERS)
        facilities = api_responce.json()

        for facility_id, facility_name in facilities.items():
            if "historical only" in facility_name.lower():
                continue

            try:
                responce = await client.get(
                    URL,
                    headers=HEADERS,
                    params={"facility": facility_id}
                )
                carpark_details = responce.json()

                total = int(carpark_details["spots"])
                occupied = int(carpark_details["occupancy"]["total"])

                results[facility_id] = {
                    "name": facility_name,
                    "free": total - occupied,
                    "total": total,
                    "occupied": occupied,
                    "last_updated": carpark_details["MessageDate"]
                }

                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"[ERROR] Facility {facility_id} ({facility_name}): {e}")
                continue
    end_time = time.perf_counter()  # ⏱ end timer
    print(f"Cache update finished in {end_time - start_time:.2f} seconds")
    print(responce)
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