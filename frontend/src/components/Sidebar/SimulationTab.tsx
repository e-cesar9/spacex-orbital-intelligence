import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useStore } from '@/stores/useStore'
import { simulateDeorbit } from '@/services/api'
import { PlayCircle, RotateCcw, AlertTriangle, Sun, Radio } from 'lucide-react'

export function SimulationTab() {
  const { selectedSatelliteId } = useStore()

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <PlayCircle size={16} className="text-spacex-accent" />
          <h3 className="font-medium">Orbital Simulation</h3>
        </div>
        <p className="text-sm text-gray-400">
          Run simulations to predict orbital behavior, deorbit trajectories, 
          and collision scenarios.
        </p>
      </div>

      {/* Deorbit Simulation */}
      <DeorbitSimulation satelliteId={selectedSatelliteId} />

      {/* Eclipse Prediction */}
      <EclipsePrediction satelliteId={selectedSatelliteId} />
      
      {/* Link Budget */}
      <LinkBudgetCard satelliteId={selectedSatelliteId} />
    </div>
  )
}

function EclipsePrediction({ satelliteId }: { satelliteId: string | null }) {
  const { data, isLoading } = useQuery({
    queryKey: ['eclipse', satelliteId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/analysis/eclipse/${satelliteId}?hours_ahead=24`)
      return res.json()
    },
    enabled: !!satelliteId,
    staleTime: 60000,
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sun size={16} className="text-yellow-400" />
          <h3 className="font-medium">Eclipse Prediction</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to predict eclipse periods.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sun size={16} className="text-yellow-400" />
        <h3 className="font-medium">Eclipse Prediction</h3>
      </div>
      
      {isLoading ? (
        <div className="animate-pulse h-16 bg-spacex-border rounded" />
      ) : data?.eclipses?.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs text-gray-400">
            {data.eclipse_count} eclipse(s) in next 24h
          </div>
          {data.eclipses.slice(0, 3).map((eclipse: any, i: number) => (
            <div key={i} className="bg-spacex-card rounded p-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Start:</span>
                <span>{new Date(eclipse.start).toLocaleTimeString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Duration:</span>
                <span>{eclipse.duration_minutes} min</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-green-400">
          ☀️ No eclipses predicted in next 24h
        </div>
      )}
    </div>
  )
}

function LinkBudgetCard({ satelliteId }: { satelliteId: string | null }) {
  const [station, setStation] = useState('Cape Canaveral')
  
  const { data, isLoading } = useQuery({
    queryKey: ['link-budget', satelliteId, station],
    queryFn: async () => {
      const res = await fetch(`/api/v1/analysis/link-budget/${satelliteId}?ground_station=${encodeURIComponent(station)}`)
      return res.json()
    },
    enabled: !!satelliteId,
    staleTime: 30000,
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Radio size={16} className="text-cyan-400" />
          <h3 className="font-medium">Link Budget</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to calculate link budget.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Radio size={16} className="text-cyan-400" />
        <h3 className="font-medium">Link Budget</h3>
      </div>
      
      <select
        value={station}
        onChange={(e) => setStation(e.target.value)}
        className="w-full mb-3 bg-spacex-card border border-spacex-border rounded px-2 py-1.5 text-sm"
      >
        <option>Cape Canaveral</option>
        <option>Vandenberg</option>
        <option>Alaska (Fairbanks)</option>
        <option>Hawaii (AMOS)</option>
        <option>Svalbard (SvalSat)</option>
      </select>
      
      {isLoading ? (
        <div className="animate-pulse h-20 bg-spacex-border rounded" />
      ) : data?.link_performance ? (
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">Elevation</span>
            <span>{data.geometry.elevation_deg.toFixed(1)}°</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Slant Range</span>
            <span>{data.geometry.slant_range_km.toFixed(0)} km</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Path Loss</span>
            <span>{data.losses.total_loss_db.toFixed(1)} dB</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Link Status</span>
            <span className={`px-2 py-0.5 rounded text-xs ${
              data.link_performance.link_status === 'GOOD' ? 'bg-green-500/20 text-green-400' :
              data.link_performance.link_status === 'MARGINAL' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {data.link_performance.link_status}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Link Margin</span>
            <span className={data.link_performance.link_margin_db > 0 ? 'text-green-400' : 'text-red-400'}>
              {data.link_performance.link_margin_db.toFixed(1)} dB
            </span>
          </div>
        </div>
      ) : data?.detail ? (
        <div className="text-sm text-red-400">{data.detail}</div>
      ) : (
        <div className="text-sm text-gray-400">No data available</div>
      )}
    </div>
  )
}

function DeorbitSimulation({ satelliteId }: { satelliteId: string | null }) {
  const [deltaV, setDeltaV] = useState(0.1)
  
  const mutation = useMutation({
    mutationFn: () => simulateDeorbit(satelliteId!, deltaV),
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <RotateCcw size={16} className="text-yellow-400" />
          <h3 className="font-medium">Deorbit Simulation</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to simulate its deorbit trajectory.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <RotateCcw size={16} className="text-yellow-400" />
        <h3 className="font-medium">Deorbit Simulation</h3>
      </div>

      <div className="space-y-4">
        <div className="text-sm">
          <span className="text-gray-400">Target: </span>
          <span className="font-mono">{satelliteId}</span>
        </div>

        {/* Delta-V slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Deorbit ΔV</span>
            <span>{deltaV.toFixed(2)} km/s</span>
          </div>
          <input
            type="range"
            min={0.01}
            max={1.0}
            step={0.01}
            value={deltaV}
            onChange={(e) => setDeltaV(parseFloat(e.target.value))}
            className="w-full accent-spacex-accent"
          />
        </div>

        {/* Run button */}
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full py-2 bg-spacex-accent hover:bg-blue-600 disabled:opacity-50 rounded-lg text-sm font-medium transition"
        >
          {mutation.isPending ? 'Simulating...' : 'Run Simulation'}
        </button>

        {/* Results */}
        {mutation.data && (
          <div className="mt-4 p-3 bg-spacex-card rounded-lg border border-spacex-border">
            <h4 className="font-medium text-sm mb-2">Simulation Results</h4>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-gray-400">Initial Altitude</div>
                <div>{mutation.data.initial_altitude_km?.toFixed(1)} km</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Reentry Time</div>
                <div>{mutation.data.estimated_reentry_hours} hours</div>
              </div>
            </div>

            {/* Trajectory preview */}
            <div className="mt-3">
              <div className="text-xs text-gray-400 mb-1">Altitude Decay</div>
              <div className="h-24 bg-spacex-dark rounded flex items-end p-2 gap-0.5">
                {mutation.data.trajectory_sample?.slice(0, 30).map((point: { altitude_km: number }, i: number) => (
                  <div
                    key={i}
                    className="flex-1 bg-gradient-to-t from-red-500 to-blue-500 rounded-t"
                    style={{ 
                      height: `${Math.max(5, (point.altitude_km / mutation.data.initial_altitude_km) * 100)}%` 
                    }}
                  />
                ))}
              </div>
            </div>

            <div className="mt-2 flex items-center gap-1 text-xs text-yellow-400">
              <AlertTriangle size={12} />
              Simplified model - actual results may vary
            </div>
          </div>
        )}

        {mutation.error && (
          <div className="text-sm text-red-400">
            Simulation failed. Please try again.
          </div>
        )}
      </div>
    </div>
  )
}
