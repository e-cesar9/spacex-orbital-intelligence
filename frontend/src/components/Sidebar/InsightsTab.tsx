import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  RotateCcw, 
  AlertTriangle, 
  Cloud,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Target
} from 'lucide-react'

export function InsightsTab() {
  return (
    <div className="space-y-4">
      {/* Turnaround Time */}
      <TurnaroundTimeCard />
      
      {/* Cross-Mission Analysis */}
      <CrossMissionCard />
      
      {/* Anomaly Timeline */}
      <AnomalyTimelineCard />
      
      {/* Weather Impact */}
      <WeatherImpactCard />
    </div>
  )
}

function TurnaroundTimeCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-turnaround'],
    queryFn: async () => {
      const res = await fetch('/api/v1/analytics/turnaround-time')
      return res.json()
    },
    staleTime: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-40" />
  }

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <RotateCcw size={16} className="text-green-400" />
          <h3 className="font-medium">Turnaround Time</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold font-mono text-green-400">
            {data?.fleet_stats?.average_turnaround_days || 0}d
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && data && (
        <div className="px-4 pb-4 space-y-3">
          {/* Fleet stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-green-400">
                {data.fleet_stats.average_turnaround_days}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Avg Days</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-blue-400">
                {data.fleet_stats.fastest_turnaround_days}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Record</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-purple-400">
                {data.fleet_stats.total_reflights}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Reflights</div>
            </div>
          </div>
          
          {/* Top performers */}
          <div>
            <div className="text-xs text-gray-400 mb-2">Top Performers</div>
            <div className="space-y-1">
              {data.top_performers?.slice(0, 5).map((booster: any) => (
                <div 
                  key={booster.booster}
                  className="flex justify-between items-center text-xs bg-spacex-card rounded px-2 py-1.5"
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      booster.status === 'active' ? 'bg-green-500' : 'bg-gray-500'
                    }`} />
                    <span className="font-mono text-gray-300">{booster.booster}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">{booster.total_flights} flights</span>
                    <span className="font-mono text-green-400">{booster.average_turnaround_days}d avg</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function CrossMissionCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-cross-mission'],
    queryFn: async () => {
      const res = await fetch('/api/v1/analytics/cross-mission')
      return res.json()
    },
    staleTime: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-20" />
  }

  const missionTypes = data?.mission_type_stats ? Object.entries(data.mission_type_stats) : []

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Target size={16} className="text-purple-400" />
          <h3 className="font-medium">Cross-Mission Learning</h3>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {expanded && data && (
        <div className="px-4 pb-4 space-y-3">
          {/* Mission type breakdown */}
          <div className="space-y-2">
            {missionTypes.map(([type, stats]: [string, any]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-24 text-xs text-gray-400 truncate">{type}</div>
                <div className="flex-1 h-1.5 bg-spacex-card rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"
                    style={{ width: `${stats.success_rate}%` }}
                  />
                </div>
                <div className="w-16 text-xs text-gray-500 text-right font-mono">
                  {stats.total_launches}
                </div>
              </div>
            ))}
          </div>
          
          {/* Insight */}
          {data.insight && (
            <div className="text-xs text-gray-400 bg-spacex-card rounded-lg p-2">
              💡 {data.insight}
            </div>
          )}
          
          {/* Most versatile boosters */}
          <div>
            <div className="text-xs text-gray-400 mb-2">Most Versatile Boosters</div>
            <div className="flex flex-wrap gap-1">
              {data.most_versatile_boosters?.slice(0, 5).map((b: any) => (
                <span 
                  key={b.booster}
                  className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs font-mono"
                >
                  {b.booster} ({b.versatility_score} types)
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AnomalyTimelineCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-anomalies'],
    queryFn: async () => {
      const res = await fetch('/api/v1/analytics/anomaly-timeline')
      return res.json()
    },
    staleTime: 300000,
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-20" />
  }

  const trend = data?.trend === 'improving' ? (
    <TrendingUp size={14} className="text-green-400" />
  ) : (
    <TrendingDown size={14} className="text-yellow-400" />
  )

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-400" />
          <h3 className="font-medium">Anomaly Timeline</h3>
        </div>
        <div className="flex items-center gap-2">
          {trend}
          <span className="text-xs text-gray-400 capitalize">{data?.trend}</span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && data && (
        <div className="px-4 pb-4 space-y-3">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-green-400">
                {data.summary.success_rate}%
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Success</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-red-400">
                {data.summary.total_failures}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Failures</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-yellow-400">
                {data.summary.boosters_lost}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Lost</div>
            </div>
          </div>
          
          {/* Timeline */}
          <div>
            <div className="text-xs text-gray-400 mb-2">Recent Anomalies</div>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {data.timeline?.slice(0, 10).map((event: any, i: number) => (
                <div 
                  key={i}
                  className={`text-xs p-2 rounded-lg border-l-2 ${
                    event.severity === 'critical' 
                      ? 'bg-red-500/10 border-red-500' 
                      : 'bg-yellow-500/10 border-yellow-500'
                  }`}
                >
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-300">{event.mission}</span>
                    <span className="text-gray-500 font-mono">
                      {new Date(event.date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-gray-400 mt-0.5 text-[11px]">
                    {event.type.replace(/_/g, ' ')}
                  </div>
                  {event.lesson_learned && (
                    <div className="text-green-400 mt-1 text-[10px]">
                      ✓ {event.lesson_learned}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function WeatherImpactCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-weather'],
    queryFn: async () => {
      const res = await fetch('/api/v1/analytics/weather-impact?months=12')
      return res.json()
    },
    staleTime: 600000, // 10 min
  })

  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-40" />
  }

  const launchpads = data?.launchpad_stats ? Object.entries(data.launchpad_stats) : []

  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Cloud size={16} className="text-cyan-400" />
          <h3 className="font-medium">Weather Impact</h3>
          <span className="px-1.5 py-0.5 text-[10px] bg-green-500/20 text-green-400 rounded">
            LIVE
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {data?.launches_with_weather_data || 0}/{data?.total_launches_analyzed || 0}
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && data && (
        <div className="px-4 pb-4 space-y-3">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-cyan-400">
                {data.launches_with_weather_data}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">W/ Weather</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-yellow-400">
                {data.high_wind_launches?.length || 0}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">High Wind</div>
            </div>
            <div className="bg-spacex-card rounded-lg p-2 text-center">
              <div className="text-lg font-bold font-mono text-blue-400">
                {launchpads.length}
              </div>
              <div className="text-[10px] text-gray-500 uppercase">Pads</div>
            </div>
          </div>
          
          {/* High wind launches */}
          {data.high_wind_launches?.length > 0 && (
            <div>
              <div className="text-xs text-yellow-400 mb-2 flex items-center gap-1">
                ⚠️ High Wind Launches (&gt;25 km/h)
              </div>
              <div className="space-y-1">
                {data.high_wind_launches.slice(0, 3).map((l: any, i: number) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-spacex-card rounded px-2 py-1.5">
                    <span className="text-gray-300 truncate max-w-[140px]">{l.mission}</span>
                    <span className="font-mono text-yellow-400">{l.wind_kmh} km/h</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weather breakdown by pad */}
          <div>
            <div className="text-xs text-gray-400 mb-2">By Launchpad</div>
            <div className="space-y-2">
              {launchpads.slice(0, 4).map(([name, stats]: [string, any]) => (
                <div key={name} className="bg-spacex-card rounded-lg p-2">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium text-gray-300">{name}</span>
                    <span className="text-xs font-mono text-cyan-400">
                      {stats.total_launches}
                    </span>
                  </div>
                  {/* Weather breakdown bar */}
                  {stats.weather_breakdown && (
                    <div className="flex h-1.5 rounded-full overflow-hidden bg-spacex-border">
                      {stats.weather_breakdown.clear > 0 && (
                        <div 
                          className="bg-green-500" 
                          style={{ width: `${(stats.weather_breakdown.clear / 10) * 100}%` }}
                          title={`Clear: ${stats.weather_breakdown.clear}`}
                        />
                      )}
                      {stats.weather_breakdown.cloudy > 0 && (
                        <div 
                          className="bg-gray-400" 
                          style={{ width: `${(stats.weather_breakdown.cloudy / 10) * 100}%` }}
                          title={`Cloudy: ${stats.weather_breakdown.cloudy}`}
                        />
                      )}
                      {stats.weather_breakdown.rain > 0 && (
                        <div 
                          className="bg-blue-500" 
                          style={{ width: `${(stats.weather_breakdown.rain / 10) * 100}%` }}
                          title={`Rain: ${stats.weather_breakdown.rain}`}
                        />
                      )}
                      {stats.weather_breakdown.high_wind > 0 && (
                        <div 
                          className="bg-yellow-500" 
                          style={{ width: `${(stats.weather_breakdown.high_wind / 10) * 100}%` }}
                          title={`High Wind: ${stats.weather_breakdown.high_wind}`}
                        />
                      )}
                    </div>
                  )}
                  <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                    <span>☀️ {stats.weather_breakdown?.clear || 0}</span>
                    <span>☁️ {stats.weather_breakdown?.cloudy || 0}</span>
                    <span>🌧️ {stats.weather_breakdown?.rain || 0}</span>
                    <span>💨 {stats.weather_breakdown?.high_wind || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Insights */}
          {data.weather_insights?.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-2">Insights</div>
              <div className="space-y-1">
                {data.weather_insights.slice(0, 3).map((insight: any, i: number) => (
                  <div key={i} className="text-[11px] text-gray-400 bg-spacex-card rounded p-2">
                    <div className="font-medium text-gray-300">{insight.insight}</div>
                    {insight.detail && (
                      <div className="text-gray-500 mt-0.5">{insight.detail}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Data source */}
          <div className="text-[10px] text-gray-600 text-center pt-1 border-t border-spacex-border">
            📡 {data.data_source}
          </div>
        </div>
      )}
    </div>
  )
}
