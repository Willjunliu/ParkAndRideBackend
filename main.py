from collections import deque
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

URL = "https://api.transport.nsw.gov.au/v1/carpark"
HEADERS = {"Authorization": f"apikey {APIKEY}"}

# Each entry: {"timestamp": float, "data": {facility_id: {...}}}
HISTORY: deque = deque(maxlen=100)

CACHE = {}
LAST_UPDATED = 0
CACHE_SECONDS = 60

TREND_WINDOW = 15 * 60  # 15 minutes in seconds


@app.get("/test")
def test_key():
    return {"key_exists": APIKEY is not None}


async def fetch_parks():
    results = {}
    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=15) as client:
        api_response = await client.get(URL, headers=HEADERS)
        facilities = api_response.json()

        last_response = None
        for facility_id, facility_name in facilities.items():
            if "historical only" in facility_name.lower():
                continue

            try:
                response = await client.get(
                    URL,
                    headers=HEADERS,
                    params={"facility": facility_id}
                )
                last_response = response
                carpark_details = response.json()

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

    end_time = time.perf_counter()
    print(f"Cache update finished in {end_time - start_time:.2f} seconds")
    if last_response:
        print(last_response)
    return results


def occupancy_change(current_data: dict) -> dict:
    """
    For each facility in current_data, find the snapshot closest to
    TREND_WINDOW seconds ago and compute the change in occupied spots.

    Returns a dict mapping facility_id -> delta_occupied
    (positive = more cars now, negative = fewer cars now)
    """
    now = time.time()
    target_time = now - TREND_WINDOW

    if not HISTORY:
        return {}

    # Find the snapshot whose timestamp is closest to target_time
    best = min(HISTORY, key=lambda h: abs(h["timestamp"] - target_time))

    # Only use it if it's within a reasonable window (±5 min of target)
    if abs(best["timestamp"] - target_time) > 5 * 60:
        return {}

    deltas = {}
    for facility_id, current in current_data.items():
        past = best["data"].get(facility_id)
        if past is not None:
            deltas[facility_id] = current["occupied"] - past["occupied"]

    return deltas


async def updater():
    global CACHE, LAST_UPDATED

    while True:
        try:
            print("Updating cache...")
            new_data = await fetch_parks()

            if new_data:
                CACHE = new_data
                LAST_UPDATED = time.time()
                HISTORY.append({"timestamp": LAST_UPDATED, "data": new_data})
                print(f"Cache updated. History length: {len(HISTORY)}")

        except Exception as e:
            print("Updater error:", e)

        await asyncio.sleep(CACHE_SECONDS)


@app.get("/parks")
def get_parks():
    deltas = occupancy_change(CACHE)

    data_with_trends = {}
    for facility_id, park in CACHE.items():
        data_with_trends[facility_id] = {
            **park,
            # delta_occupied: positive = more cars, negative = fewer cars
            # None means not enough history yet
            "delta_occupied": deltas.get(facility_id, None),
        }

    return {
        "last_updated": LAST_UPDATED,
        "trend_window_minutes": TREND_WINDOW // 60,
        "data": data_with_trends
    }