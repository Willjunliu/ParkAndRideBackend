# Better Park & Ride

A real-time carpark availability web application for NSW that helps drivers find available parking and understand how carpark occupancy changes over time.

## 🌐 Live Demo

**[Visit Better Park & Ride](YOUR_WEBSITE_URL)**

The application retrieves real-time carpark data from Transport for NSW and provides occupancy trends using data collected over time.

## ✨ Features

* 🚗 **Real-time availability** — View the current number of available and occupied spaces.
* 📈 **Occupancy trends** — See how occupancy has changed over the previous 15 minutes.
* 📊 **Historical data** — Explore previously recorded carpark occupancy.
* 🔄 **Automatic updates** — Carpark data is collected automatically every 60 seconds.
* ☁️ **Cloud database** — Historical snapshots are stored using Turso.
* ⚡ **REST API** — FastAPI backend providing carpark and historical data.
* 📱 **Web interface** — Interactive frontend for browsing carpark availability.

## 🖥️ Screenshots

<!-- Add screenshots of your website here -->

![Better Park & Ride](screenshots/homepage.png)

## 🏗️ Architecture

```text
                 Transport for NSW API
                          │
                          ▼
                  ┌───────────────┐
                  │ FastAPI       │
                  │ Backend       │
                  └───────┬───────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          In-memory Cache         Turso
          Current data         Historical data
                │                   │
                └─────────┬─────────┘
                          ▼
                     Web Frontend
                          │
                          ▼
                       User
```

The backend periodically retrieves carpark data from the Transport for NSW API.

The latest results are kept in an in-memory cache for fast access, while timestamped snapshots are stored in Turso for historical analysis.

## 🛠️ Tech Stack

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

## 🔌 API

The backend provides the following endpoints:

| Endpoint                           | Description                                                |
| ---------------------------------- | ---------------------------------------------------------- |
| `GET /parks`                       | Returns current carpark availability and occupancy trends  |
| `GET /parks/{facility_id}/history` | Returns historical occupancy data for a carpark            |
| `GET /ping`                        | API health check                                           |
| `GET /test`                        | Checks whether the Transport for NSW API key is configured |

## 📈 Data Collection

A background task runs continuously while the backend is running.

Every 60 seconds it:

1. Requests the latest carpark information from Transport for NSW.
2. Updates the in-memory cache.
3. Records a timestamped snapshot in Turso.
4. Removes snapshots older than seven days.

This allows Better Park & Ride to provide both current availability and historical occupancy information.

## 🔐 Environment Variables

The backend requires the following environment variables:

```env
API_KEY=your_transport_nsw_api_key
TURSO_URL=your_turso_database_url
TURSO_TOKEN=your_turso_auth_token
```

These values should **not** be committed to the repository.

## 🚀 Running Locally

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd better-park-and-ride
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables and start the backend:

```bash
uvicorn main:app --reload
```

The API will then be available at:

```text
http://127.0.0.1:8000
```

## 📁 Project Structure

```text
better-park-and-ride/
│
├── backend/
│   ├── main.py
│   └── ...
│
├── website/
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── ...
│
├── requirements.txt
├── .gitignore
└── README.md
```

> The exact structure may differ depending on the current repository layout.

## 🗺️ Future Improvements

* [ ] Add map-based carpark discovery
* [ ] Add carpark search and filtering
* [ ] Improve historical data visualisation
* [ ] Add longer-term occupancy trends
* [ ] Add availability predictions
* [ ] Add automated backend tests
* [ ] Improve mobile responsiveness

## 📄 Data Source

Carpark information is provided by **Transport for NSW** through its public Car Park API.

## 👤 Author

**William Liu**

Computer Science student at UTS.
