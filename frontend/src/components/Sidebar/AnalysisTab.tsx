import { useQuery } from '@tanstack/react-query'
import { getAltitudeDistribution, getConstellationHealth, getCollisionAlerts } from '@/services/api'
import { AlertTriangle, Shield, Layers, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

export function AnalysisTab() {
  return (
    <div className="space-y-4">
      {/* Constellation Health */}
      <ConstellationHealthCard />
      
      {/* Collision Alerts */}
      <CollisionAlertsCard />
      
      {/* Altitude Distribution */}
      <AltitudeDistributionCard />
    </div>
  )
}

function ConstellationHealthCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['constellation-health'],
    queryFn: getConstellationHealth,
    staleTime: 60000,
    refetchInterval: 120000, // Refresh every 2 min
  })

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-green-400" />
          <h3 className="font-medium">Constellation Health</h3>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {expanded && (
        <div className="px-4 pb-4">
          {isLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-16 bg-spacex-border rounded" />
              <div className="h-24 bg-spacex-border rounded" />
            </div>
          ) : error ? (
            <div className="text-red-400 text-sm">Failed to load health data</div>
          ) : data && (
            <div className="space-y-4">
              {/* Overall Stats */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-spacex-card rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-green-400">
                    {data.operational_percentage}%
                  </div>
                  <div className="text-xs text-gray-400">Operational</div>
                </div>
                <div className="bg-spacex-card rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {data.total_tracked.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-400">Tracked</div>
                </div>
                <div className="bg-spacex-card rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-yellow-400">
                    {data.anomaly_count}
                  </div>
                  <div className="text-xs text-gray-400">Anomalies</div>
                </div>
              </div>
              
              {/* Shell Health */}
              <div className="space-y-2">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Orbital Shells</div>
                {data.shells.map(shell => (
                  <div key={shell.shell} className="bg-spacex-card rounded p-2">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm">{shell.shell}</span>
                      <span className="text-xs text-gray-400">{shell.satellite_count} sats</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-spacex-border rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            shell.health_score > 80 ? 'bg-green-500' :
                            shell.health_score > 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${shell.health_score}%` }}
                        />
                      </div>
                      <span className="text-xs w-8">{shell.health_score.toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Anomalies */}
              {data.anomalies.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-gray-400 uppercase tracking-wide flex items-center gap-1">
                    <AlertTriangle size={12} className="text-yellow-400" />
                    Anomalies Detected
                  </div>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {data.anomalies.slice(0, 5).map(a => (
                      <div 
                        key={a.satellite_id}
                        className={`text-xs p-2 rounded ${
                          a.urgency === 'HIGH' ? 'bg-red-500/20 text-red-300' : 'bg-yellow-500/20 text-yellow-300'
                        }`}
                      >
                        <span className="font-mono">{a.name}</span>
                        <span className="ml-2 text-gray-400">
                          {a.altitude_km}km · {a.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function CollisionAlertsCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading } = useQuery({
    queryKey: ['collision-alerts'],
    queryFn: () => getCollisionAlerts(0.3),
    staleTime: 30000,
    refetchInterval: 60000, // Refresh every minute
  })

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-400" />
          <h3 className="font-medium">Collision Alerts</h3>
          {data && data.alert_count > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-red-500/30 text-red-400 rounded">
              {data.alert_count}
            </span>
          )}
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {expanded && (
        <div className="px-4 pb-4">
          {isLoading ? (
            <div className="animate-pulse h-24 bg-spacex-border rounded" />
          ) : data?.alerts.length === 0 ? (
            <div className="text-center py-4 text-gray-400 text-sm">
              <Shield className="w-8 h-8 mx-auto mb-2 text-green-400" />
              No collision alerts
            </div>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {data?.alerts.map((alert, i) => (
                <div 
                  key={i}
                  className={`p-2 rounded text-sm ${
                    alert.severity === 'HIGH' ? 'bg-red-500/20 border border-red-500/30' :
                    alert.severity === 'MEDIUM' ? 'bg-yellow-500/20 border border-yellow-500/30' :
                    'bg-spacex-card'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="font-mono text-xs">{alert.satellite_1.name}</div>
                      <div className="font-mono text-xs text-gray-400">↔ {alert.satellite_2.name}</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xs font-medium ${
                        alert.severity === 'HIGH' ? 'text-red-400' :
                        alert.severity === 'MEDIUM' ? 'text-yellow-400' : 'text-gray-400'
                      }`}>
                        {alert.distance_km} km
                      </div>
                      <div className="text-xs text-gray-500">
                        Risk: {(alert.risk_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AltitudeDistributionCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data, isLoading } = useQuery({
    queryKey: ['altitude-distribution'],
    queryFn: getAltitudeDistribution,
    staleTime: 300000, // 5 min
  })

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Layers size={16} className="text-blue-400" />
          <h3 className="font-medium">Altitude Distribution</h3>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {expanded && (
        <div className="px-4 pb-4">
          {isLoading ? (
            <div className="animate-pulse h-32 bg-spacex-border rounded" />
          ) : data && (
            <div className="space-y-2">
              {data.distribution.map(band => (
                <div key={band.band} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span>{band.band}</span>
                    <span className="text-gray-400">{band.count.toLocaleString()}</span>
                  </div>
                  <div className="h-2 bg-spacex-border rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
                      style={{ width: `${band.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
