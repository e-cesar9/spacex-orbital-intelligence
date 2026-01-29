import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLaunches, getCores, getFleetStats, getLiveLaunches, getNextLaunch, compareDataSources } from '@/services/api'
import { 
  RotateCcw, 
  CheckCircle, 
  XCircle, 
  Clock, 
  ExternalLink, 
  Video,
  AlertTriangle,
  Zap,
  Rocket
} from 'lucide-react'

export function LaunchesTab() {
  const [dataSource, setDataSource] = useState<'live' | 'historical'>('live')
  const [showUpcoming, setShowUpcoming] = useState(true)
  const [spacexOnly, setSpacexOnly] = useState(true)

  return (
    <div className="space-y-4">
      {/* Data Source Indicator */}
      <DataSourceCard />
      
      {/* Next Launch Countdown */}
      <NextLaunchCard />
      
      {/* Data Source Toggle */}
      <div className="flex gap-1 p-1 bg-spacex-card rounded-lg">
        <button
          onClick={() => setDataSource('live')}
          className={`flex-1 py-1.5 text-xs rounded-md transition flex items-center justify-center gap-1 ${
            dataSource === 'live' 
              ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <Zap size={12} />
          Live Data
        </button>
        <button
          onClick={() => setDataSource('historical')}
          className={`flex-1 py-1.5 text-xs rounded-md transition flex items-center justify-center gap-1 ${
            dataSource === 'historical' 
              ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' 
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <Clock size={12} />
          Historical
        </button>
      </div>

      {dataSource === 'live' ? (
        <>
          {/* Live Controls */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowUpcoming(true)}
              className={`flex-1 py-2 text-sm rounded-lg transition ${
                showUpcoming ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
              }`}
            >
              Upcoming
            </button>
            <button
              onClick={() => setShowUpcoming(false)}
              className={`flex-1 py-2 text-sm rounded-lg transition ${
                !showUpcoming ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
              }`}
            >
              Recent
            </button>
          </div>
          
          <button
            onClick={() => setSpacexOnly(!spacexOnly)}
            className={`w-full py-1.5 text-xs rounded-lg transition ${
              spacexOnly 
                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' 
                : 'bg-spacex-dark text-gray-400'
            }`}
          >
            {spacexOnly ? '🚀 SpaceX Only' : '🌍 All Agencies'}
          </button>
          
          <LiveLaunchesCard upcoming={showUpcoming} spacexOnly={spacexOnly} />
        </>
      ) : (
        <>
          {/* Historical Stats */}
          <FleetStatsCard />
          <CoresCard />
          
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
            <div className="flex items-center gap-2 text-yellow-400 text-xs mb-1">
              <AlertTriangle size={12} />
              Historical Data Notice
            </div>
            <p className="text-[10px] text-gray-400">
              SpaceX API discontinued in 2022. Historical data shown for analysis purposes only.
            </p>
          </div>
          
          <HistoricalLaunchesCard />
        </>
      )}
    </div>
  )
}

function DataSourceCard() {
  const { data } = useQuery({
    queryKey: ['data-source-compare'],
    queryFn: compareDataSources,
    staleTime: 300000,
  })

  if (!data) return null

  return (
    <div className="bg-spacex-dark rounded-lg p-3">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-gray-400">Data Freshness</span>
        <span className="text-[10px] text-gray-500">{data.data_gap_days} day gap</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-gray-400">Live: Today</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-gray-400">Historical: 2022</span>
        </div>
      </div>
    </div>
  )
}

function NextLaunchCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['next-launch-spacex'],
    queryFn: () => getNextLaunch(true),
    refetchInterval: 60000, // Refresh every minute
  })

  if (isLoading || !data?.launch) return null

  const isLive = data.countdown.total_seconds <= 0
  const days = Math.abs(data.countdown.days)
  const hours = Math.abs(data.countdown.hours)
  const minutes = Math.abs(data.countdown.minutes)

  return (
    <div className="bg-gradient-to-r from-spacex-accent/20 to-blue-600/20 rounded-lg p-4 border border-spacex-accent/30">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Rocket size={16} className="text-spacex-accent" />
          <span className="text-xs text-gray-400">Next SpaceX Launch</span>
        </div>
        {isLive ? (
          <span className="px-2 py-0.5 text-[10px] bg-green-500/30 text-green-400 rounded animate-pulse">
            LAUNCHED
          </span>
        ) : (
          <span className="px-2 py-0.5 text-[10px] bg-spacex-accent/30 text-spacex-accent rounded">
            T-{days}d {hours}h {minutes}m
          </span>
        )}
      </div>
      
      <div className="text-sm font-medium text-white mb-1">
        {data.launch.mission?.name || data.launch.name}
      </div>
      
      <div className="flex justify-between text-[10px] text-gray-400">
        <span>{data.launch.pad?.location}</span>
        <span>{new Date(data.launch.date_utc).toLocaleDateString()}</span>
      </div>
      
      {data.launch.webcast && (
        <a
          href={data.launch.webcast}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 flex items-center gap-1 text-xs text-spacex-accent hover:underline"
        >
          <Video size={12} />
          Watch Live
        </a>
      )}
    </div>
  )
}

function LiveLaunchesCard({ upcoming, spacexOnly }: { upcoming: boolean; spacexOnly: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ['live-launches', upcoming, spacexOnly],
    queryFn: () => getLiveLaunches(15, upcoming, spacexOnly),
    staleTime: 60000,
  })

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-spacex-dark rounded-lg p-3 h-20" />
        ))}
      </div>
    )
  }

  if (!data?.launches?.length) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        No launches found
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-xs text-gray-500">
        <span>{data.count} launches</span>
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          {data.source}
        </span>
      </div>
      
      {data.launches.map(launch => (
        <div 
          key={launch.id}
          className="bg-spacex-dark rounded-lg p-3 hover:bg-spacex-border/50 transition"
        >
          <div className="flex items-start gap-3">
            {launch.image && (
              <img 
                src={launch.image} 
                alt={launch.name}
                className="w-12 h-12 rounded object-cover"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm truncate">
                  {launch.mission?.name || launch.name}
                </span>
                {launch.status === 'Success' && (
                  <CheckCircle size={12} className="text-green-400 shrink-0" />
                )}
                {launch.status === 'Failure' && (
                  <XCircle size={12} className="text-red-400 shrink-0" />
                )}
              </div>
              
              <div className="text-xs text-gray-400 mt-0.5">
                {launch.rocket?.name} • {launch.agency}
              </div>
              
              <div className="flex justify-between items-center mt-1">
                <span className="text-[10px] text-gray-500">
                  {launch.pad?.location?.split(',')[0]}
                </span>
                <span className="text-[10px] text-gray-500">
                  {new Date(launch.date_utc).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
          
          {launch.webcast && (
            <a
              href={launch.webcast}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 flex items-center gap-1 text-xs text-spacex-accent hover:underline"
            >
              Watch <ExternalLink size={10} />
            </a>
          )}
        </div>
      ))}
    </div>
  )
}

function FleetStatsCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['fleet-stats'],
    queryFn: getFleetStats,
    staleTime: 60000,
  })

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 gap-3 animate-pulse">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-spacex-dark rounded-lg p-3 h-16" />
        ))}
      </div>
    )
  }

  const stats = [
    { label: 'Starlink', value: data.total_starlink.toLocaleString(), color: 'text-blue-400' },
    { label: 'Launches', value: data.total_launches.toLocaleString(), color: 'text-green-400' },
    { label: 'Success Rate', value: `${data.success_rate}%`, color: 'text-yellow-400' },
    { label: 'Last 30 Days', value: data.launches_last_30_days.toString(), color: 'text-purple-400' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {stats.map(stat => (
        <div key={stat.label} className="stat-card">
          <div className="text-xs text-gray-400">{stat.label}</div>
          <div className={`text-xl font-bold ${stat.color}`}>{stat.value}</div>
        </div>
      ))}
    </div>
  )
}

function CoresCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['cores'],
    queryFn: () => getCores(10),
    staleTime: 60000,
  })

  if (isLoading || !data) return null

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <RotateCcw size={16} className="text-spacex-accent" />
        <h3 className="font-medium">Reusable Boosters</h3>
        <span className="text-[10px] text-yellow-400 bg-yellow-500/20 px-1.5 py-0.5 rounded">
          2022 Data
        </span>
      </div>

      <div className="text-xs text-gray-400 mb-2">
        Total reuses: {data.total_reuses} | Active: {data.active_cores}
      </div>
      
      <div className="flex flex-wrap gap-1">
        {data.cores.slice(0, 8).map(core => (
          <div
            key={core.id}
            className={`
              px-2 py-1 rounded text-xs font-mono
              ${core.status === 'active' 
                ? 'bg-green-500/20 text-green-400' 
                : core.status === 'lost'
                ? 'bg-red-500/20 text-red-400'
                : 'bg-gray-500/20 text-gray-400'
              }
            `}
            title={`${core.serial}: ${core.reuse_count} flights`}
          >
            {core.serial} ({core.reuse_count})
          </div>
        ))}
      </div>
    </div>
  )
}

function HistoricalLaunchesCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['historical-launches'],
    queryFn: () => getLaunches(10, false),
    staleTime: 60000,
  })

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-spacex-dark rounded-lg" />
  }

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 flex justify-between">
        <span>Historical Launches (2022)</span>
        <span className="text-yellow-400">SpaceX API</span>
      </div>
      
      {data?.launches.slice(0, 5).map(launch => (
        <div 
          key={launch.id}
          className="bg-spacex-dark rounded-lg p-3"
        >
          <div className="flex justify-between items-start">
            <div>
              <div className="font-medium text-sm">{launch.name}</div>
              <div className="text-xs text-gray-400">
                {new Date(launch.date_utc).toLocaleDateString()}
              </div>
            </div>
            {launch.success === true && <CheckCircle size={14} className="text-green-400" />}
            {launch.success === false && <XCircle size={14} className="text-red-400" />}
          </div>
        </div>
      ))}
    </div>
  )
}
