# Better Park And Ride Backend

A real-time carpark availability web application for NSW that helps drivers find available parking and understand how carpark occupancy changes over time.

## Live Demo

**[Visit Better Park And Ride](https://puuggordo.github.io/BetterParkAndRide/)**

The application retrieves real-time carpark data from Transport for NSW and provides occupancy trends using data collected over time.

## Features

*  **Real-time availability** — View the current number of available and occupied spaces.
*  **Occupancy trends** — See how occupancy has changed over the previous 15 minutes.
*  **Historical data** — Explore previously recorded carpark occupancy.
*  **Automatic updates** — Carpark data is collected automatically every 60 seconds.
*  **Cloud database** — Historical snapshots are stored using Turso.
*  **REST API** — FastAPI backend providing carpark and historical data.
*  **Web interface** — Interactive frontend for browsing carpark availability.

## Architecture

```text
                  ┌─────────────────────────┐
                  │  TRANSPORT FOR NSW API  │
                  │       Live Data         │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │      FASTAPI BACKEND    │
                  │   Fetch & Process Data  │
                  └────────────┬────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │   IN-MEMORY     │         │      TURSO      │
        │     CACHE       │         │     DATABASE    │
        │                 │         │                 │
        │ Current data    │         │ Historical data │
        │ 60s cache       │         │ Occupancy logs  │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                  ┌─────────────────────────┐
                  │     DATA PROCESSING     │
                  │                         │
                  │ • Occupancy             │
                  │ • Free spaces           │
                  │ • 15-min changes        │
                  │ • Historical queries    │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │       REST API          │
                  │                         │
                  │   /parks                │
                  │   /parks/{id}/history   │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │      WEB FRONTEND       │
                  └─────────────────────────┘
```

The backend periodically retrieves carpark data from the Transport for NSW API.

The latest results are kept in an in-memory cache for fast access, while timestamped snapshots are stored in Turso for historical analysis.

##  Tech Stack

**Frontend**

* HTML
* CSS
* JavaScript
* Chart.js

**Backend**

* Python
* FastAPI
* HTTPX

**Database**

* Turso
* libSQL

**Deployment**

* Render

**Data Source**

* Transport for NSW Car Park API

##  API

The backend provides the following endpoints:

| Endpoint                           | Description                                                |
| ---------------------------------- | ---------------------------------------------------------- |
| `GET /parks`                       | Returns current carpark availability and occupancy trends  |
| `GET /parks/{facility_id}/history` | Returns historical occupancy data for a carpark            |
| `GET /ping`                        | API health check                                           |
| `GET /test`                        | Checks whether the Transport for NSW API key is configured |

## Data Collection

A background task runs continuously while the backend is running.

Every 60 seconds it:

1. Requests the latest carpark information from Transport for NSW.
2. Updates the in-memory cache.
3. Records a timestamped snapshot in Turso.
4. Removes snapshots older than seven days.

This allows Better Park And Ride to provide both current availability and historical occupancy information.

## Environment Variables

The backend requires the following environment variables:

```env
API_KEY=your_transport_nsw_api_key
TURSO_URL=your_turso_database_url
TURSO_TOKEN=your_turso_auth_token
```

These values should **not** be committed to the repository.


## Future Improvements

* [ ] Add map-based carpark discovery
* [ ] Add carpark search and filtering
* [ ] Improve historical data visualisation
* [ ] Add longer-term occupancy trends
* [ ] Add availability predictions
* [ ] Add automated backend tests
* [ ] Improve mobile responsiveness

## Data Source

Carpark information is provided by **Transport for NSW** through its public Car Park API.
