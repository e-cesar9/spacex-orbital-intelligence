import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Activity, Target, Globe, ChevronRight } from 'lucide-react'

export function OpsTab() {
  return (
    <div className="space-y-4">
      {/* Fleet Health KPIs */}
      <FleetHealthCard />
      
      {/* Conjunction Workflow */}
      <ConjunctionWorkflowCard />
      
      {/* Coverage Analysis */}
      <CoverageAnalysisCard />
    </div>
  )
}

function FleetHealthCard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ops-fleet-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/fleet/health')
      return res.json()
    },
    refetchInterval: 60000, // 1 min
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-48" />
  }

  if (error || !data) {
    return <div className="text-red-400 text-sm">Failed to load fleet health</div>
  }

  const healthColor = data.fleet_health_score >= 80 ? 'text-green-400' : 
                      data.fleet_health_score >= 60 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-blue-400" />
          <h3 className="font-semibold">Fleet Health</h3>
        </div>
        <div className={`text-2xl font-bold ${healthColor}`}>
          {data.fleet_health_score}%
        </div>
      </div>
      
      {/* Data freshness */}
      <div className={`text-xs mb-3 px-2 py-1 rounded inline-block ${
        data.data_freshness?.status === 'FRESH' ? 'bg-green-500/20 text-green-400' :
        data.data_freshness?.status === 'STALE' ? 'bg-yellow-500/20 text-yellow-400' :
        'bg-red-500/20 text-red-400'
      }`}>
        TLE: {data.data_freshness?.tle_age_human} ({data.data_freshness?.status})
      </div>
      
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-spacex-card rounded p-2 text-center">
          <div className="text-lg font-bold text-green-400">{data.summary?.operational || 0}</div>
          <div className="text-xxs text-gray-400">Operational</div>
        </div>
        <div className="bg-spacex-card rounded p-2 text-center">
          <div className="text-lg font-bold text-blue-400">{data.summary?.raising || 0}</div>
          <div className="text-xxs text-gray-400">Raising</div>
        </div>
        <div className="bg-spacex-card rounded p-2 text-center">
          <div className="text-lg font-bold text-red-400">{data.summary?.decaying || 0}</div>
          <div className="text-xxs text-gray-400">Decaying</div>
        </div>
      </div>
      
      {/* Alerts */}
      {(data.alerts?.critical_count > 0 || data.alerts?.warning_count > 0) && (
        <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
          <div className="flex items-center gap-2 text-red-400 text-sm font-medium mb-2">
            <AlertTriangle size={14} />
            Action Required
          </div>
          <div className="space-y-1 text-xs">
            {data.alerts.critical_count > 0 && (
              <div className="text-red-300">
                🔴 {data.alerts.critical_count} satellites in critical decay
              </div>
            )}
            {data.alerts.warning_count > 0 && (
              <div className="text-yellow-300">
                🟡 {data.alerts.warning_count} satellites need monitoring
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Decaying satellites list */}
      {data.action_required?.decaying_satellites?.length > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 mb-2">Urgent: Decaying Satellites</div>
          <div className="max-h-24 overflow-y-auto space-y-1">
            {data.action_required.decaying_satellites.slice(0, 5).map((sat: any) => (
              <div key={sat.id} className="flex justify-between items-center text-xs bg-spacex-card rounded px-2 py-1">
                <span className="font-mono">{sat.name}</span>
                <span className={sat.status === 'CRITICAL' ? 'text-red-400' : 'text-yellow-400'}>
                  {sat.altitude_km} km
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ConjunctionWorkflowCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['ops-conjunction-workflow'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/conjunctions/workflow')
      return res.json()
    },
    refetchInterval: 300000, // 5 min
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-32" />
  }

  const statusColor = data?.workflow_status === 'GREEN' ? 'bg-green-500' :
                      data?.workflow_status === 'YELLOW' ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target size={18} className="text-orange-400" />
          <h3 className="font-semibold">Conjunction Workflow</h3>
        </div>
        <div className={`w-3 h-3 rounded-full ${statusColor}`} />
      </div>
      
      {/* Workflow summary */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className={`rounded p-2 text-center ${
          (data?.summary?.mitigate || 0) > 0 ? 'bg-red-500/20 border border-red-500/30' : 'bg-spacex-card'
        }`}>
          <div className="text-lg font-bold text-red-400">{data?.summary?.mitigate || 0}</div>
          <div className="text-xxs text-gray-400">MITIGATE</div>
        </div>
        <div className={`rounded p-2 text-center ${
          (data?.summary?.assess || 0) > 0 ? 'bg-yellow-500/20 border border-yellow-500/30' : 'bg-spacex-card'
        }`}>
          <div className="text-lg font-bold text-yellow-400">{data?.summary?.assess || 0}</div>
          <div className="text-xxs text-gray-400">ASSESS</div>
        </div>
        <div className="bg-spacex-card rounded p-2 text-center">
          <div className="text-lg font-bold text-green-400">{data?.summary?.screen || 0}</div>
          <div className="text-xxs text-gray-400">SCREEN</div>
        </div>
      </div>
      
      {/* Mitigate actions */}
      {data?.action_required?.mitigate?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-red-400 font-medium">⚠️ Maneuver Required:</div>
          {data.action_required.mitigate.slice(0, 3).map((item: any) => (
            <div key={item.cdm_id} className="bg-red-500/10 border border-red-500/30 rounded p-2 text-xs">
              <div className="flex justify-between">
                <span className="font-mono">{item.satellite_1?.name}</span>
                <span className="text-red-400">Pc: {(item.probability * 100).toFixed(4)}%</span>
              </div>
              <div className="text-gray-400 mt-1">
                TCA: {new Date(item.tca).toLocaleString()}
              </div>
              <div className="text-green-400 mt-1 flex items-center gap-1">
                <ChevronRight size={12} />
                {item.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {data?.workflow_status === 'GREEN' && (
        <div className="text-center py-4 text-green-400 text-sm">
          ✓ No conjunction actions required
        </div>
      )}
    </div>
  )
}

function CoverageAnalysisCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['ops-coverage'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/coverage/analysis')
      return res.json()
    },
    staleTime: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-32" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Globe size={18} className="text-cyan-400" />
          <h3 className="font-semibold">Global Coverage</h3>
        </div>
        <div className="text-xl font-bold text-cyan-400">
          {data?.global_coverage_score || 0}%
        </div>
      </div>
      
      {/* Coverage by region */}
      <div className="space-y-2">
        {data?.coverage_by_region?.map((region: any) => (
          <div key={region.region} className="flex items-center gap-2">
            <div className="w-24 text-xs text-gray-400 truncate">{region.region}</div>
            <div className="flex-1 h-2 bg-spacex-card rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${
                  region.status === 'OPTIMAL' ? 'bg-green-500' :
                  region.status === 'ADEQUATE' ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, region.coverage_score)}%` }}
              />
            </div>
            <div className="w-12 text-xs text-right">{region.satellite_count}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
