import { useQuery } from '@tanstack/react-query'
import { getAltitudeDistribution, getHotspots, getSatelliteRisk } from '@/services/api'
import { useStore } from '@/stores/useStore'
import { AlertTriangle, Layers, MapPin } from 'lucide-react'

export function AnalysisTab() {
  const { selectedSatelliteId } = useStore()

  return (
    <div className="space-y-6">
      {/* Altitude Distribution */}
      <AltitudeDistributionCard />

      {/* Collision Hotspots */}
      <HotspotsCard />

      {/* Selected satellite risk */}
      {selectedSatelliteId && (
        <RiskAnalysisCard satelliteId={selectedSatelliteId} />
      )}
    </div>
  )
}

function AltitudeDistributionCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['altitude-distribution'],
    queryFn: getAltitudeDistribution,
    staleTime: 60000,
  })

  if (isLoading) {
    return <LoadingCard title="Altitude Distribution" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Layers size={16} className="text-spacex-accent" />
        <h3 className="font-medium">Altitude Distribution</h3>
      </div>

      {data && (
        <div className="space-y-2">
          <div className="text-xs text-gray-400 mb-2">
            Total: {data.total_satellites.toLocaleString()} satellites
          </div>
          {data.distribution.map(band => (
            <div key={band.band} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span>{band.band}</span>
                <span className="text-gray-400">
                  {band.count.toLocaleString()} ({band.percentage}%)
                </span>
              </div>
              <div className="h-2 bg-spacex-border rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-spacex-accent to-blue-400 rounded-full transition-all"
                  style={{ width: `${band.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function HotspotsCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['hotspots'],
    queryFn: getHotspots,
    staleTime: 60000,
  })

  if (isLoading) {
    return <LoadingCard title="Collision Hotspots" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <MapPin size={16} className="text-red-400" />
        <h3 className="font-medium">Collision Hotspots</h3>
      </div>

      {data && (
        <div className="space-y-2">
          <div className="text-xs text-gray-400 mb-2">
            High-density orbital regions
          </div>
          {data.hotspots.slice(0, 5).map((hotspot, i) => (
            <div 
              key={i}
              className="p-2 bg-spacex-card rounded border border-spacex-border"
            >
              <div className="flex justify-between items-center">
                <div className="text-sm">
                  <span className="text-gray-400">Lat:</span> {hotspot.latitude_zone}°
                  <span className="text-gray-400 ml-2">Alt:</span> {hotspot.altitude_band} km
                </div>
                <div className={`
                  px-2 py-0.5 rounded text-xs font-medium
                  ${hotspot.count >= 50 ? 'bg-red-500/20 text-red-400' : 
                    hotspot.count >= 30 ? 'bg-yellow-500/20 text-yellow-400' : 
                    'bg-green-500/20 text-green-400'}
                `}>
                  {hotspot.count} sats
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function RiskAnalysisCard({ satelliteId }: { satelliteId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['satellite-risk', satelliteId],
    queryFn: () => getSatelliteRisk(satelliteId, 24),
    staleTime: 30000,
  })

  if (isLoading) {
    return <LoadingCard title="Collision Risk Analysis" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle size={16} className="text-yellow-400" />
        <h3 className="font-medium">Risk Analysis</h3>
      </div>

      {data && (
        <div className="space-y-3">
          <div className="text-xs text-gray-400">
            {data.name || data.satellite_id} @ {data.altitude_km.toFixed(0)} km
          </div>
          <div className="text-xs text-gray-400">
            Analyzed {data.nearby_count} nearby objects
          </div>

          {data.risks.length > 0 ? (
            <div className="space-y-2">
              {data.risks.map((risk, i) => (
                <div 
                  key={i}
                  className={`p-2 rounded border ${getRiskClass(risk.risk_score)}`}
                >
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-mono text-xs">{risk.satellite_2}</span>
                    <span className="font-bold">
                      {(risk.risk_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Min distance: {risk.min_distance_km.toFixed(1)} km
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-green-400">
              ✓ No significant collision risks detected
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function LoadingCard({ title: _title }: { title: string }) {
  return (
    <div className="bg-spacex-dark rounded-lg p-4 animate-pulse">
      <div className="h-4 bg-spacex-border rounded w-1/2 mb-3" />
      <div className="space-y-2">
        <div className="h-3 bg-spacex-border rounded w-full" />
        <div className="h-3 bg-spacex-border rounded w-3/4" />
        <div className="h-3 bg-spacex-border rounded w-1/2" />
      </div>
    </div>
  )
}

function getRiskClass(score: number): string {
  if (score >= 0.7) return 'risk-high border-red-500/30'
  if (score >= 0.3) return 'risk-medium border-yellow-500/30'
  return 'risk-low border-green-500/30'
}
