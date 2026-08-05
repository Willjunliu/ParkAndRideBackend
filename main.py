from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
import httpx
import asyncio
import os
import time
import libsql_client
from fastapi.middleware.cors import CORSMiddleware

APIKEY = os.getenv("API_KEY")
TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")


URL = "https://api.transport.nsw.gov.au/v1/carpark"
HEADERS = {"Authorization": f"apikey {APIKEY}"}

CACHE = {}
LAST_UPDATED = 0
CACHE_SECONDS = 60

TREND_WINDOW = 15 * 60  # 15 minutes in seconds
KEEP_DAYS     = 7


def make_client():
    return libsql_client.create_client(
        url = TURSO_URL,
        auth_token = TURSO_TOKEN
    )

async def db_init():
    async with make_client() as client:
        await client.batch([
            """
           CREATE TABLE IF NOT EXISTS snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          REAL    NOT NULL,
                facility_id TEXT    NOT NULL,
                occupied    INTEGER NOT NULL,
                total       INTEGER NOT NULL
            )
            """,
             "CREATE INDEX IF NOT EXISTS idx_ts  ON snapshots(ts)",
            "CREATE INDEX IF NOT EXISTS idx_fac ON snapshots(facility_id, ts)",
        ])
    print(f"[DB] Initialised — {TURSO_URL}")

async def db_insert_snapshot(ts: float, data: dict):
    statements = [
        libsql_client.Statement(
            "INSERT INTO snapshots (ts, facility_id, occupied, total) VALUES (?, ?, ?, ?)",
            [ts, facility_id, park["occupied"], park["total"]],
        )
        for facility_id, park in data.items()
    ]
    async with make_client() as client:
        await client.batch(statements)
 
 
async def db_purge_old():
    cutoff = time.time() - KEEP_DAYS * 86400
    async with make_client() as client:
        await client.execute(
            "DELETE FROM snapshots WHERE ts < ?", [cutoff]
        )
 

async def db_get_week_ago_history(facility_id: str):
    now = time.time()

    start_time = now - (15 * 60)
    end_time = now - (0 * 60)

    async with make_client() as client:
        result = await client.execute(
            """
            SELECT ts, occupied, total
            FROM snapshots
            WHERE facility_id = ?
              AND ts BETWEEN ? AND ?
            ORDER BY ts ASC
            """,
            [
                facility_id,
                start_time,
                end_time
            ],
        )

    history = []

    for row in result.rows:
        ts, occupied, total = row

        history.append({
            "timestamp": ts,
            "occupied": occupied,
            "free": total - occupied,
            "total": total
        })

    return history

 
async def db_occupancy_change(current_data: dict):
    """
    For each facility, find the snapshot closest to TREND_WINDOW seconds ago
    and return the delta in occupied spots.
    Tolerance: ±5 min around the target timestamp.
    """
    now       = time.time()
    target_ts = now - TREND_WINDOW
    tolerance = 5 * 60
 
    deltas = {}
    async with make_client() as client:
        for facility_id, current in current_data.items():
            result = await client.execute(
                """
                SELECT occupied
                FROM   snapshots
                WHERE  facility_id = ?
                  AND  ts BETWEEN ? AND ?
                ORDER  BY ABS(ts - ?) ASC
                LIMIT  1
                """,
                [
                    facility_id,
                    target_ts - tolerance,
                    target_ts + tolerance,
                    target_ts,
                ],
            )
            if result.rows:
                past_occupied = result.rows[0][0]
                deltas[facility_id] = current["occupied"] - past_occupied
 
    return deltas



@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_init()
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




async def updater():
    global CACHE, LAST_UPDATED

    while True:
        try:
            print("Updating cache...")
            new_data = await fetch_parks()

            if new_data:
                CACHE = new_data
                LAST_UPDATED = time.time()

                await db_insert_snapshot(LAST_UPDATED, new_data)

                await db_purge_old()

                print(f"Cache updated. {len(new_data)} facilities")

        except Exception as e:
            print("Updater error:", e)

        await asyncio.sleep(CACHE_SECONDS)







@app.get("/test")
def test_key():
    return {"key_exists": APIKEY is not None}


@app.get("/parks")
async def get_parks():
    deltas = await db_occupancy_change(CACHE)

    data_with_trends = {}
    for facility_id, park in CACHE.items():
        data_with_trends[facility_id] = {
            **park,
            # delta_occupied: positive = more cars, negative = fewer cars
            # None means not enough history yet
            "delta_occupied": deltas.get(facility_id),
        }

    return {
        "last_updated": LAST_UPDATED,
        "trend_window_minutes": TREND_WINDOW // 60,
        "data": data_with_trends
    }


@app.get("/parks/{facility_id}/history")
async def get_park_history(facility_id: str):
    history = await db_get_week_ago_history(facility_id)

    return {
        "facility_id": facility_id,
        "period": "same time last week",
        "data": history
    }

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.head("/ping")
def ping_head():
    return Response(status_code=200)