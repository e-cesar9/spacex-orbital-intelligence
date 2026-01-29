import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { 
  AlertTriangle, 
  Activity, 
  Target, 
  Globe, 
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  TrendingUp
} from 'lucide-react'

export function OpsTab() {
  return (
    <div className="space-y-4">
      {/* Fleet Health KPIs */}
      <FleetHealthCard />
      
      {/* TLE Freshness Indicator */}
      <TLEFreshnessCard />
      
      {/* Conjunction Workflow */}
      <ConjunctionWorkflowCard />
      
      {/* Decision Recommendations */}
      <DecisionRecommendationsCard />
      
      {/* Coverage Analysis */}
      <CoverageAnalysisCard />
    </div>
  )
}

function FleetHealthCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['ops-fleet-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/fleet/health')
      return res.json()
    },
    refetchInterval: 60000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-32" />
  }

  if (error || !data) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="text-red-400 text-sm">Failed to load fleet health</div>
      </div>
    )
  }

  const healthColor = data.fleet_health_score >= 80 ? 'text-green-400' : 
                      data.fleet_health_score >= 60 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-blue-400" />
          <h3 className="font-medium">Fleet Health</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xl font-bold font-mono ${healthColor}`}>
            {data.fleet_health_score}%
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-green-400">
                {data.summary?.operational || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Operational</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-blue-400">
                {data.summary?.raising || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Raising</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-red-400">
                {data.summary?.decaying || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Decaying</div>
            </div>
          </div>
          
          {/* Alerts */}
          {(data.alerts?.critical_count > 0 || data.alerts?.warning_count > 0) && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <div className="flex items-center gap-2 text-red-400 text-xs font-medium mb-2">
                <AlertTriangle size={12} />
                ACTION REQUIRED
              </div>
              <div className="space-y-1 text-xs font-mono">
                {data.alerts.critical_count > 0 && (
                  <div className="text-red-300">
                    CRIT: {data.alerts.critical_count} satellites in decay
                  </div>
                )}
                {data.alerts.warning_count > 0 && (
                  <div className="text-yellow-300">
                    WARN: {data.alerts.warning_count} need monitoring
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Decaying satellites list */}
          {data.action_required?.decaying_satellites?.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-2">Decay Queue</div>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {data.action_required.decaying_satellites.slice(0, 5).map((sat: any) => (
                  <div key={sat.id} className="flex justify-between items-center text-xs bg-spacex-card rounded px-2 py-1.5">
                    <span className="font-mono text-gray-300">{sat.name}</span>
                    <span className={`font-mono ${sat.status === 'CRITICAL' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {sat.altitude_km} km
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TLEFreshnessCard() {
  const { data } = useQuery({
    queryKey: ['ops-fleet-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/fleet/health')
      return res.json()
    },
    staleTime: 60000,
  })

  if (!data?.data_freshness) return null

  const freshness = data.data_freshness
  const statusColor = freshness.status === 'FRESH' ? 'bg-green-500' :
                      freshness.status === 'STALE' ? 'bg-yellow-500' : 'bg-red-500'
  const textColor = freshness.status === 'FRESH' ? 'text-green-400' :
                    freshness.status === 'STALE' ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-gray-400" />
          <span className="text-sm text-gray-400">TLE Data Age</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className={`text-sm font-mono ${textColor}`}>
            {freshness.tle_age_human}
          </span>
        </div>
      </div>
    </div>
  )
}

function ConjunctionWorkflowCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading } = useQuery({
    queryKey: ['ops-conjunction-workflow'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/conjunctions/workflow')
      return res.json()
    },
    refetchInterval: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-32" />
  }

  const statusColor = data?.workflow_status === 'GREEN' ? 'bg-green-500' :
                      data?.workflow_status === 'YELLOW' ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Target size={16} className="text-orange-400" />
          <h3 className="font-medium">Conjunction Workflow</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Workflow summary */}
          <div className="grid grid-cols-3 gap-2">
            <div className={`rounded-lg p-2 text-center ${
              (data?.summary?.mitigate || 0) > 0 
                ? 'bg-red-500/20 border border-red-500/30' 
                : 'bg-spacex-card'
            }`}>
              <div className="text-lg font-bold font-mono text-red-400">
                {data?.summary?.mitigate || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Mitigate</div>
            </div>
            <div className={`rounded-lg p-2 text-center ${
              (data?.summary?.assess || 0) > 0 
                ? 'bg-yellow-500/20 border border-yellow-500/30' 
                : 'bg-spacex-card'
            }`}>
              <div className="text-lg font-bold font-mono text-yellow-400">
                {data?.summary?.assess || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Assess</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-green-400">
                {data?.summary?.screen || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Screen</div>
            </div>
          </div>
          
          {/* Mitigate actions */}
          {data?.action_required?.mitigate?.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-red-400 font-medium flex items-center gap-1">
                <Zap size={12} />
                Maneuver Required
              </div>
              {data.action_required.mitigate.slice(0, 3).map((item: any) => (
                <div key={item.cdm_id} className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-xs">
                  <div className="flex justify-between">
                    <span className="font-mono text-gray-200">{item.satellite_1?.name}</span>
                    <span className="text-red-400 font-mono">Pc: {(item.probability * 100).toFixed(4)}%</span>
                  </div>
                  <div className="text-gray-500 mt-1 font-mono text-[10px]">
                    TCA: {new Date(item.tca).toLocaleString()}
                  </div>
                  <div className="text-green-400 mt-1 flex items-center gap-1">
                    <ChevronRight size={10} />
                    <span>{item.recommendation}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {data?.workflow_status === 'GREEN' && (
            <div className="text-center py-3 text-green-400 text-sm">
              ✓ No conjunction actions required
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DecisionRecommendationsCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data: healthData } = useQuery({
    queryKey: ['ops-fleet-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/fleet/health')
      return res.json()
    },
    staleTime: 60000,
  })
  
  const { data: conjunctionData } = useQuery({
    queryKey: ['ops-conjunction-workflow'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/conjunctions/workflow')
      return res.json()
    },
    staleTime: 300000,
  })

  // Generate recommendations based on data
  const recommendations: { priority: 'high' | 'medium' | 'low'; text: string }[] = []
  
  if (healthData?.alerts?.critical_count > 0) {
    recommendations.push({
      priority: 'high',
      text: `Review ${healthData.alerts.critical_count} satellites in critical decay`
    })
  }
  
  if (conjunctionData?.summary?.mitigate > 0) {
    recommendations.push({
      priority: 'high',
      text: `Execute ${conjunctionData.summary.mitigate} collision avoidance maneuver(s)`
    })
  }
  
  if (healthData?.data_freshness?.status === 'STALE') {
    recommendations.push({
      priority: 'medium',
      text: 'TLE data is stale - request fresh ephemeris'
    })
  }
  
  if (healthData?.summary?.decaying > 10) {
    recommendations.push({
      priority: 'medium',
      text: `${healthData.summary.decaying} satellites decaying - plan re-boost operations`
    })
  }

  if (recommendations.length === 0) {
    recommendations.push({
      priority: 'low',
      text: 'All systems nominal - no actions required'
    })
  }

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-purple-400" />
          <h3 className="font-medium">Recommendations</h3>
          {recommendations.some(r => r.priority === 'high') && (
            <span className="px-1.5 py-0.5 text-[10px] bg-red-500/30 text-red-400 rounded uppercase">
              Action
            </span>
          )}
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {recommendations.map((rec, i) => (
            <div 
              key={i}
              className={`flex items-start gap-2 p-2 rounded-lg text-xs ${
                rec.priority === 'high' ? 'bg-red-500/10 border border-red-500/30' :
                rec.priority === 'medium' ? 'bg-yellow-500/10 border border-yellow-500/30' :
                'bg-spacex-card'
              }`}
            >
              <span className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                rec.priority === 'high' ? 'bg-red-500' :
                rec.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
              }`} />
              <span className="text-gray-300">{rec.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CoverageAnalysisCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data, isLoading } = useQuery({
    queryKey: ['ops-coverage'],
    queryFn: async () => {
      const res = await fetch('/api/v1/ops/coverage/analysis')
      return res.json()
    },
    staleTime: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-16" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-cyan-400" />
          <h3 className="font-medium">Global Coverage</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold font-mono text-cyan-400">
            {data?.global_coverage_score || 0}%
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {data?.coverage_by_region?.map((region: any) => (
            <div key={region.region} className="flex items-center gap-2">
              <div className="w-20 text-xs text-gray-400 truncate">{region.region}</div>
              <div className="flex-1 h-1.5 bg-spacex-card rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full ${
                    region.status === 'OPTIMAL' ? 'bg-green-500' :
                    region.status === 'ADEQUATE' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, region.coverage_score)}%` }}
                />
              </div>
              <div className="w-8 text-xs text-gray-500 text-right font-mono">
                {region.satellite_count}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
