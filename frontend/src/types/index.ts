// Satellite types
export interface SatellitePosition {
  id: string
  lat: number
  lon: number
  alt: number
  v?: number // velocity
  name?: string
}

export interface SatelliteDetail {
  satellite_id: string
  timestamp: string
  position: { x: number; y: number; z: number }
  velocity: { vx: number; vy: number; vz: number }
  geographic: { latitude: number; longitude: number; altitude: number }
  speed: number
  name?: string
}

export interface OrbitPoint {
  t: string
  lat: number
  lon: number
  alt: number
}

export interface OrbitData {
  satellite_id: string
  name: string
  hours: number
  orbit: OrbitPoint[]
}

// Risk types
export interface CollisionRisk {
  satellite_1: string
  satellite_2: string
  min_distance_km: number
  tca: string
  risk_score: number
  other_name?: string
}

export interface DensityData {
  target_altitude: number
  tolerance: number
  count: number
  density_per_1000km: number
  satellites: { id: string; altitude: number; name?: string }[]
}

export interface AltitudeDistribution {
  total_satellites: number
  distribution: {
    band: string
    altitude_min: number
    altitude_max: number
    count: number
    percentage: number
  }[]
}

export interface Hotspot {
  latitude_zone: number
  altitude_band: number
  count: number
  satellites: string[]
}

// Launch types
export interface Launch {
  id: string
  name: string
  date_utc: string
  success: boolean | null
  rocket_id: string
  details: string | null
  payload_count: number
  webcast: string | null
  patch: string | null
}

export interface Core {
  id: string
  serial: string
  reuse_count: number
  status: string
  last_update: string | null
  launch_count: number
}

export interface FleetStats {
  total_starlink: number
  total_launches: number
  total_cores: number
  success_rate: number
  launches_last_30_days: number
}

// WebSocket message types
export interface WSPositionsMessage {
  type: 'positions'
  count: number
  data: SatellitePosition[]
}

export interface WSSatelliteMessage {
  type: 'satellite'
  data: SatelliteDetail
}

export type WSMessage = WSPositionsMessage | WSSatelliteMessage | { type: 'ping' } | { type: 'pong' }
