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
