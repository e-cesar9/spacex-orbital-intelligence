import { useQuery } from '@tanstack/react-query'
import { useStore } from '@/stores/useStore'
import { getSatellite } from '@/services/api'
import { Search, X, MapPin, Gauge, Clock } from 'lucide-react'

export function SatellitesTab() {
  const { 
    satellites, 
    selectedSatelliteId, 
    selectSatellite,
    searchQuery,
    setSearchQuery,
    altitudeRange,
    setAltitudeRange,
    showOrbits,
    setShowOrbits,
    autoRotate,
    setAutoRotate,
    showEarthTexture,
    setShowEarthTexture
  } = useStore()

  // Filter satellites
  const filteredSatellites = satellites.filter(s => {
    if (searchQuery && !s.id.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    return s.alt >= altitudeRange[0] && s.alt <= altitudeRange[1]
  })

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="space-y-3">
        {/* Search */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search satellites..."
            className="w-full pl-4 pr-9 py-2 bg-spacex-dark rounded-lg border border-spacex-border focus:border-spacex-accent focus:outline-none text-sm"
          />
          {searchQuery ? (
            <button 
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
            >
              <X size={14} />
            </button>
          ) : (
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          )}
        </div>

        {/* Altitude filter */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Altitude Range</span>
            <span>{altitudeRange[0]} - {altitudeRange[1]} km</span>
          </div>
          <input
            type="range"
            min={200}
            max={2000}
            value={altitudeRange[1]}
            onChange={(e) => setAltitudeRange([altitudeRange[0], parseInt(e.target.value)])}
            className="w-full accent-spacex-accent"
          />
        </div>

        {/* Toggles */}
        <div className="flex gap-2">
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            className={`flex-1 py-1.5 text-xs rounded-lg transition ${
              autoRotate ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
            }`}
          >
            Auto Rotate
          </button>
          <button
            onClick={() => setShowOrbits(!showOrbits)}
            className={`flex-1 py-1.5 text-xs rounded-lg transition ${
              showOrbits ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
            }`}
          >
            Show Orbits
          </button>
        </div>
        
        {/* Earth texture toggle */}
        <button
          onClick={() => setShowEarthTexture(!showEarthTexture)}
          className={`w-full py-1.5 text-xs rounded-lg transition ${
            showEarthTexture ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/30' : 'bg-spacex-dark text-gray-400'
          }`}
        >
          {showEarthTexture ? '🌍 NASA Texture' : '🔵 Minimal Globe'}
        </button>
      </div>

      {/* Selected satellite details */}
      {selectedSatelliteId && (
        <SelectedSatelliteCard 
          satelliteId={selectedSatelliteId}
          onClose={() => selectSatellite(null)}
        />
      )}

      {/* Satellite list */}
      <div className="space-y-1">
        <div className="text-xs text-gray-400 mb-2">
          Showing {filteredSatellites.length} satellites
        </div>
        <div className="max-h-96 overflow-y-auto space-y-1">
          {filteredSatellites.slice(0, 100).map(sat => (
            <button
              key={sat.id}
              onClick={() => selectSatellite(sat.id)}
              className={`
                w-full text-left p-2 rounded-lg text-sm transition
                ${selectedSatelliteId === sat.id 
                  ? 'bg-spacex-accent/20 border border-spacex-accent' 
                  : 'bg-spacex-dark hover:bg-spacex-border'
                }
              `}
            >
              <div className="flex justify-between items-center">
                <span className="font-mono text-xs">{sat.id}</span>
                <span className="text-xs text-gray-400">{sat.alt.toFixed(0)} km</span>
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {sat.lat.toFixed(2)}°, {sat.lon.toFixed(2)}°
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function SelectedSatelliteCard({ 
  satelliteId, 
  onClose 
}: { 
  satelliteId: string
  onClose: () => void 
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['satellite', satelliteId],
    queryFn: () => getSatellite(satelliteId),
    staleTime: 5000,
  })

  if (isLoading || !data) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-spacex-border rounded w-1/2 mb-2" />
        <div className="h-3 bg-spacex-border rounded w-3/4" />
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4 border border-spacex-accent/30">
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="font-mono text-sm">{data.satellite_id}</div>
          {data.name && <div className="text-xs text-gray-400">{data.name}</div>}
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X size={16} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="flex items-center gap-2">
          <MapPin size={14} className="text-spacex-accent" />
          <div>
            <div className="text-xs text-gray-400">Position</div>
            <div>
              {data.geographic.latitude.toFixed(2)}°, {data.geographic.longitude.toFixed(2)}°
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Gauge size={14} className="text-green-400" />
          <div>
            <div className="text-xs text-gray-400">Altitude</div>
            <div>{data.geographic.altitude.toFixed(1)} km</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-yellow-400" />
          <div>
            <div className="text-xs text-gray-400">Velocity</div>
            <div>{data.speed.toFixed(2)} km/s</div>
          </div>
        </div>
      </div>
    </div>
  )
}
