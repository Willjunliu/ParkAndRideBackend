from fastapi import FastAPI
import requests
import time
import os

apikey = os.getenv("API_KEY")
app = FastAPI()


url = "https://api.transport.nsw.gov.au/v1/carpark"
headers = {
    "Authorization": f"apikey {apikey}"
}

@app.get("/test")
def test_key():
    return {"key_exists": apikey is not None}

@app.get("/parks")
def get_all_parks():
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

            # if free_spaces <= 0:
            #     print(f"{name}: FULL")
            # else:
            #     print(f"{name}: {free_spaces} free")

            time.sleep(0.3)  # polite to the API
        except Exception as e:
            # print(f"Failed for {name}: {e}")
            continue
    return results