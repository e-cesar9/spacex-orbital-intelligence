import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useStore } from '@/stores/useStore'
import { simulateDeorbit } from '@/services/api'
import { PlayCircle, RotateCcw, AlertTriangle } from 'lucide-react'

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

      {/* Coming Soon */}
      <div className="bg-spacex-dark rounded-lg p-4 border border-dashed border-spacex-border">
        <h3 className="font-medium mb-2">Coming Soon</h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Multi-satellite collision simulation</li>
          <li>• Constellation deployment planning</li>
          <li>• Debris field propagation</li>
          <li>• Maneuver optimization</li>
        </ul>
      </div>
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
