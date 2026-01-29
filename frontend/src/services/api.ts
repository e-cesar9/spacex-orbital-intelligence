import type {
  SatellitePosition,
  SatelliteDetail,
  OrbitData,
  CollisionRisk,
  DensityData,
  AltitudeDistribution,
  Hotspot,
  Launch,
  Core,
  FleetStats,
} from '@/types'

const API_BASE = '/api/v1'

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

// Satellites
export async function getSatellites(limit = 100, offset = 0) {
  return fetchJson<{
    total: number
    satellites: (SatellitePosition & { name?: string })[]
  }>(`${API_BASE}/satellites?limit=${limit}&offset=${offset}`)
}

export async function getAllPositions() {
  return fetchJson<{
    count: number
    positions: SatellitePosition[]
  }>(`${API_BASE}/satellites/positions`)
}

export async function getSatellite(id: string) {
  return fetchJson<SatelliteDetail>(`${API_BASE}/satellites/${id}`)
}

export async function getSatelliteOrbit(id: string, hours = 24, stepMinutes = 5) {
  return fetchJson<OrbitData>(
    `${API_BASE}/satellites/${id}/orbit?hours=${hours}&step_minutes=${stepMinutes}`
  )
}

// Analysis
export async function getSatelliteRisk(id: string, hoursAhead = 24) {
  return fetchJson<{
    satellite_id: string
    name: string
    altitude_km: number
    nearby_count: number
    risks: CollisionRisk[]
  }>(`${API_BASE}/analysis/risk/${id}?hours_ahead=${hoursAhead}`)
}

export async function getDensity(altitudeKm = 550, toleranceKm = 50) {
  return fetchJson<DensityData>(
    `${API_BASE}/analysis/density?altitude_km=${altitudeKm}&tolerance_km=${toleranceKm}`
  )
}

export async function getAltitudeDistribution() {
  return fetchJson<AltitudeDistribution>(`${API_BASE}/analysis/density/distribution`)
}

export async function getHotspots() {
  return fetchJson<{
    total_satellites: number
    hotspots: Hotspot[]
  }>(`${API_BASE}/analysis/hotspots`)
}

export async function getConstellationHealth() {
  return fetchJson<{
    total_tracked: number
    total_operational: number
    operational_percentage: number
    shells: {
      shell: string
      target_altitude_km: number
      satellite_count: number
      health_score: number
    }[]
    anomalies: {
      satellite_id: string
      name: string
      altitude_km: number
      status: string
      urgency: string
    }[]
    anomaly_count: number
  }>(`${API_BASE}/analysis/constellation/health`)
}

export async function getCollisionAlerts(minRisk = 0.3) {
  return fetchJson<{
    alert_count: number
    alerts: {
      satellite_1: { id: string; name: string }
      satellite_2: { id: string; name: string }
      distance_km: number
      risk_score: number
      severity: string
    }[]
  }>(`${API_BASE}/analysis/alerts?min_risk=${minRisk}`)
}

// CDM Conjunctions (real Space-Track data)
export async function getCdmConjunctions(filter = 'STARLINK', hoursAhead = 72) {
  return fetchJson<{
    source: string
    alert_count: number
    alerts: {
      cdm_id: string
      tca: string
      min_range_km: number
      probability: number
      satellite_1: { id: string; name: string; type: string }
      satellite_2: { id: string; name: string; type: string }
      emergency: boolean
    }[]
  }>(`${API_BASE}/analysis/conjunctions/cdm?satellite_filter=${filter}&hours_ahead=${hoursAhead}`)
}

// Ground Stations
export async function getGroundStations() {
  return fetchJson<{
    count: number
    stations: {
      name: string
      latitude: number
      longitude: number
      min_elevation_deg: number
    }[]
  }>(`${API_BASE}/analysis/ground-stations`)
}

export async function getGroundStationVisibility(satelliteId: string) {
  return fetchJson<{
    satellite_id: string
    name: string
    position: { latitude: number; longitude: number; altitude_km: number }
    visible_stations: {
      name: string
      latitude: number
      longitude: number
      elevation_deg: number
    }[]
    visible_count: number
  }>(`${API_BASE}/analysis/ground-stations/visibility/${satelliteId}`)
}

export async function simulateDeorbit(id: string, deltaV = 0.1) {
  const response = await fetch(
    `${API_BASE}/analysis/simulate/deorbit?satellite_id=${id}&delta_v=${deltaV}`,
    { method: 'POST' }
  )
  if (!response.ok) throw new Error(`API error: ${response.status}`)
  return response.json()
}

// Launches
export async function getLaunches(limit = 20, upcoming = false) {
  return fetchJson<{
    type: string
    count: number
    launches: Launch[]
  }>(`${API_BASE}/launches?limit=${limit}&upcoming=${upcoming}`)
}

export async function getCores(limit = 20) {
  return fetchJson<{
    count: number
    total_reuses: number
    active_cores: number
    cores: Core[]
  }>(`${API_BASE}/launches/cores?limit=${limit}`)
}

export async function getFleetStats() {
  return fetchJson<FleetStats>(`${API_BASE}/launches/statistics`)
}

export async function getLaunchTimeline(months = 12) {
  return fetchJson<{
    months: number
    past_count: number
    upcoming_count: number
    timeline: { date: string; name: string; success: boolean | null; type: string }[]
  }>(`${API_BASE}/launches/timeline?months=${months}`)
}

// Health
export async function getHealth() {
  return fetchJson<{
    status: string
    satellites_loaded: number
    cache_connected: boolean
    last_tle_update: string | null
  }>('/health')
}

// Live Launches (Launch Library 2 - CURRENT DATA)
export async function getLiveLaunches(limit = 20, upcoming = true, spacexOnly = false) {
  return fetchJson<{
    source: string
    updated_at: string
    type: string
    spacex_only: boolean
    count: number
    launches: {
      id: string
      name: string
      status: string
      date_utc: string
      rocket: { name: string; family: string }
      pad: { name: string; location: string; latitude: string; longitude: string }
      mission: { name: string; type: string; description: string }
      webcast: string | null
      image: string | null
      agency: string
    }[]
  }>(`${API_BASE}/launches-live?limit=${limit}&upcoming=${upcoming}&spacex_only=${spacexOnly}`)
}

export async function getNextLaunch(spacexOnly = false) {
  return fetchJson<{
    source: string
    launch: {
      id: string
      name: string
      status: string
      date_utc: string
      rocket: { name: string; family: string }
      pad: { name: string; location: string }
      mission: { name: string; type: string; description: string }
      webcast: string | null
      image: string | null
      agency: string
    }
    countdown: {
      days: number
      hours: number
      minutes: number
      total_seconds: number
    }
    is_spacex: boolean
  }>(`${API_BASE}/launches-live/next?spacex_only=${spacexOnly}`)
}

export async function getLiveStatistics() {
  return fetchJson<{
    source: string
    updated_at: string
    spacex: {
      recent_launches: number
      upcoming_launches: number
      success_rate: number
      market_share_pct: number
      mission_types: Record<string, number>
    }
    global: {
      recent_launches: number
      agencies: number
    }
    next_spacex: any
  }>(`${API_BASE}/launches-live/statistics`)
}

export async function compareDataSources() {
  return fetchJson<{
    spacex_api: { latest_launch: string; status: string; note: string }
    launch_library_2: { latest_launch: string; status: string; note: string }
    recommendation: string
    data_gap_days: number
  }>(`${API_BASE}/launches-live/compare`)
}
