import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLaunches, getCores, getFleetStats } from '@/services/api'
import { RotateCcw, CheckCircle, XCircle, Clock, ExternalLink, Video } from 'lucide-react'

export function LaunchesTab() {
  const [showUpcoming, setShowUpcoming] = useState(false)
  const [videoOnly, setVideoOnly] = useState(false)

  return (
    <div className="space-y-6">
      {/* Fleet Stats */}
      <FleetStatsCard />

      {/* Reusable Cores */}
      <CoresCard />

      {/* Launch toggle + filters */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <button
            onClick={() => setShowUpcoming(false)}
            className={`flex-1 py-2 text-sm rounded-lg transition ${
              !showUpcoming ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
            }`}
          >
            Past Launches
          </button>
          <button
            onClick={() => setShowUpcoming(true)}
            className={`flex-1 py-2 text-sm rounded-lg transition ${
              showUpcoming ? 'bg-spacex-accent text-white' : 'bg-spacex-dark text-gray-400'
            }`}
          >
            Upcoming
          </button>
        </div>
        
        {/* Video filter */}
        <button
          onClick={() => setVideoOnly(!videoOnly)}
          className={`w-full flex items-center justify-center gap-2 py-1.5 text-xs rounded-lg transition ${
            videoOnly ? 'bg-purple-500/30 text-purple-300 border border-purple-500/50' : 'bg-spacex-dark text-gray-400'
          }`}
        >
          <Video size={14} />
          {videoOnly ? 'Showing with video only' : 'Filter: with video'}
        </button>
      </div>

      {/* Launches list */}
      <LaunchesCard upcoming={showUpcoming} videoOnly={videoOnly} />
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
          <div key={i} className="bg-spacex-dark rounded-lg p-3">
            <div className="h-3 bg-spacex-border rounded w-1/2 mb-2" />
            <div className="h-6 bg-spacex-border rounded w-full" />
          </div>
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

  if (isLoading) return null

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <RotateCcw size={16} className="text-spacex-accent" />
        <h3 className="font-medium">Reusable Boosters</h3>
      </div>

      {data && (
        <div className="space-y-2">
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
      )}
    </div>
  )
}

function LaunchesCard({ upcoming, videoOnly }: { upcoming: boolean; videoOnly: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ['launches', upcoming],
    queryFn: () => getLaunches(30, upcoming),
    staleTime: 60000,
  })

  // Filter and sort launches
  const filteredLaunches = data?.launches
    ?.filter(launch => !videoOnly || launch.webcast)
    ?.sort((a, b) => {
      // For upcoming: ascending (soonest first)
      // For past: descending (most recent first)
      const dateA = new Date(a.date_utc).getTime()
      const dateB = new Date(b.date_utc).getTime()
      return upcoming ? dateA - dateB : dateB - dateA
    }) || []

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-spacex-dark rounded-lg p-3">
            <div className="h-4 bg-spacex-border rounded w-3/4 mb-2" />
            <div className="h-3 bg-spacex-border rounded w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (filteredLaunches.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        {videoOnly ? 'No launches with video' : 'No launches found'}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {filteredLaunches.map(launch => (
        <div 
          key={launch.id}
          className="bg-spacex-dark rounded-lg p-3 hover:bg-spacex-border/50 transition"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              {launch.patch && (
                <img 
                  src={launch.patch} 
                  alt={launch.name}
                  className="w-8 h-8 rounded"
                />
              )}
              <div>
                <div className="font-medium text-sm">{launch.name}</div>
                <div className="text-xs text-gray-400">
                  {new Date(launch.date_utc).toLocaleDateString()}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {launch.success === true && (
                <CheckCircle size={16} className="text-green-400" />
              )}
              {launch.success === false && (
                <XCircle size={16} className="text-red-400" />
              )}
              {launch.success === null && (
                <Clock size={16} className="text-yellow-400" />
              )}
            </div>
          </div>
          
          {launch.details && (
            <p className="text-xs text-gray-400 mt-2 line-clamp-2">
              {launch.details}
            </p>
          )}

          <div className="flex items-center justify-between mt-2 text-xs">
            <span className="text-gray-500">
              {launch.payload_count} payload{launch.payload_count !== 1 ? 's' : ''}
            </span>
            {launch.webcast && (
              <a
                href={launch.webcast}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-spacex-accent hover:underline"
              >
                Watch <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
