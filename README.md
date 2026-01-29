# 🚀 SpaceX Orbital Intelligence Platform

Real-time 3D visualization and intelligence platform for SpaceX's Starlink constellation, launches, and fleet operations.

![SpaceX Orbital](docs/screenshot.png)

## Features

### 🌍 3D Globe Visualization
- Interactive Earth with Three.js
- Real-time satellite positions from TLE data
- Animated orbital paths
- Color-coded altitude indicators

### 🛰️ Orbital Intelligence
- SGP4 propagation for accurate positioning
- Collision proximity detection
- Orbital density analysis
- Risk scoring per satellite

### 🚀 Fleet & Mission Tracking
- Launch history and upcoming missions
- Booster reuse statistics
- Success/anomaly tracking
- Timeline visualization

### 🔮 Simulation Mode
- Deorbit trajectory simulation
- Altitude decay prediction
- (Coming soon) Multi-satellite scenarios

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **SGP4 + Skyfield** for orbital mechanics
- **Redis** for caching
- **PostgreSQL** for persistence

### Frontend
- **React 18** + TypeScript
- **Three.js** / @react-three/fiber for 3D
- **Zustand** for state management
- **React Query** for data fetching
- **Tailwind CSS** for styling

### Infrastructure
- Docker + Docker Compose
- WebSocket for real-time updates

## Quick Start

### With Docker Compose

```bash
# Clone and start
git clone https://github.com/your-repo/spacex-orbital.git
cd spacex-orbital
docker-compose up -d

# Open http://localhost:3000
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

## API Endpoints

### Satellites
- `GET /api/v1/satellites` - List tracked satellites
- `GET /api/v1/satellites/positions` - All current positions (3D viz)
- `GET /api/v1/satellites/{id}` - Satellite details
- `GET /api/v1/satellites/{id}/orbit` - Orbital path

### Analysis
- `GET /api/v1/analysis/risk/{id}` - Collision risk assessment
- `GET /api/v1/analysis/density` - Orbital density at altitude
- `GET /api/v1/analysis/hotspots` - High-density regions
- `POST /api/v1/analysis/simulate/deorbit` - Deorbit simulation

### Launches
- `GET /api/v1/launches` - Past/upcoming launches
- `GET /api/v1/launches/cores` - Booster reuse data
- `GET /api/v1/launches/statistics` - Fleet statistics

### WebSocket
- `ws://host/ws/positions` - Real-time satellite positions

## Data Sources

- **SpaceX API** - Starlink metadata, launches, cores
- **CelesTrak** - TLE orbital elements
- **Space-Track** - Comprehensive satellite catalog (optional)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  3D Globe   │  │  Dashboard  │  │  Timeline   │     │
│  │  Three.js   │  │  Charts     │  │  Controls   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket + REST
┌─────────────────────────┼───────────────────────────────┐
│                    BACKEND (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  REST API   │  │  WebSocket  │  │  Scheduler  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                         │                               │
│              ┌──────────┴──────────┐                   │
│              │  Orbital Engine     │                   │
│              │  SGP4 Propagator    │                   │
│              └─────────────────────┘                   │
└─────────────────────────┬───────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────┴────┐    ┌──────┴──────┐   ┌─────┴─────┐
    │ SpaceX  │    │  CelesTrak  │   │   Redis   │
    │   API   │    │    TLE      │   │   Cache   │
    └─────────┘    └─────────────┘   └───────────┘
```

## Environment Variables

### Backend
```env
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
TLE_REFRESH_INTERVAL=3600
WS_BROADCAST_INTERVAL=1.0
```

## License

MIT
