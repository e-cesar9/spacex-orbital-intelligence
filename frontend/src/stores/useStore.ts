import { create } from 'zustand'
import type { SatellitePosition, SatelliteDetail } from '@/types'

interface ViewState {
  // Globe controls
  autoRotate: boolean
  showOrbits: boolean
  showLabels: boolean
  
  // Selection
  selectedSatelliteId: string | null
  selectedSatellite: SatelliteDetail | null
  
  // Filters
  altitudeRange: [number, number]
  searchQuery: string
  
  // UI state
  sidebarOpen: boolean
  activeTab: 'satellites' | 'ops' | 'insights' | 'analysis' | 'launches' | 'simulation'
  
  // Real-time data
  satellites: SatellitePosition[]
  lastUpdate: Date | null
  wsConnected: boolean
  
  // Statistics
  stats: {
    totalSatellites: number
    highRiskCount: number
    averageAltitude: number
  }
  
  // Deorbit simulation
  deorbitTrajectory: { hours: number; altitude_km: number }[] | null
  showEarthTexture: boolean
}

interface ViewActions {
  // Globe controls
  setAutoRotate: (value: boolean) => void
  setShowOrbits: (value: boolean) => void
  setShowLabels: (value: boolean) => void
  
  // Selection
  selectSatellite: (id: string | null) => void
  setSelectedSatelliteDetail: (detail: SatelliteDetail | null) => void
  
  // Filters
  setAltitudeRange: (range: [number, number]) => void
  setSearchQuery: (query: string) => void
  
  // UI
  setSidebarOpen: (open: boolean) => void
  setActiveTab: (tab: ViewState['activeTab']) => void
  
  // Data
  updateSatellites: (satellites: SatellitePosition[]) => void
  setWsConnected: (connected: boolean) => void
  
  // Deorbit
  setDeorbitTrajectory: (trajectory: { hours: number; altitude_km: number }[] | null) => void
  setShowEarthTexture: (show: boolean) => void
  
  // Reset
  reset: () => void
}

const initialState: ViewState = {
  autoRotate: true,
  showOrbits: false,
  showLabels: true,
  selectedSatelliteId: null,
  selectedSatellite: null,
  altitudeRange: [200, 2000],
  searchQuery: '',
  sidebarOpen: true,
  activeTab: 'satellites',
  satellites: [],
  lastUpdate: null,
  wsConnected: false,
  stats: {
    totalSatellites: 0,
    highRiskCount: 0,
    averageAltitude: 0,
  },
  deorbitTrajectory: null,
  showEarthTexture: true,
}

export const useStore = create<ViewState & ViewActions>((set, get) => ({
  ...initialState,
  
  setAutoRotate: (value) => set({ autoRotate: value }),
  setShowOrbits: (value) => set({ showOrbits: value }),
  setShowLabels: (value) => set({ showLabels: value }),
  
  selectSatellite: (id) => set({ 
    selectedSatelliteId: id,
    autoRotate: id ? false : get().autoRotate 
  }),
  
  setSelectedSatelliteDetail: (detail) => set({ selectedSatellite: detail }),
  
  setAltitudeRange: (range) => set({ altitudeRange: range }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  updateSatellites: (satellites) => {
    const avgAlt = satellites.length > 0
      ? satellites.reduce((sum, s) => sum + s.alt, 0) / satellites.length
      : 0
    
    set({ 
      satellites,
      lastUpdate: new Date(),
      stats: {
        totalSatellites: satellites.length,
        highRiskCount: 0, // Updated separately
        averageAltitude: Math.round(avgAlt),
      }
    })
  },
  
  setWsConnected: (connected) => set({ wsConnected: connected }),
  
  setDeorbitTrajectory: (trajectory) => set({ deorbitTrajectory: trajectory }),
  setShowEarthTexture: (show) => set({ showEarthTexture: show }),
  
  reset: () => set(initialState),
}))
