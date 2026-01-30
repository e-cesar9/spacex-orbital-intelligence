import { useStore } from '@/stores/useStore'
import { SatellitesTab } from './SatellitesTab'
import { AnalysisTab } from './AnalysisTab'
import { LaunchesTab } from './LaunchesTab'
import { SimulationTab } from './SimulationTab'
import { OpsTab } from './OpsTab'
import { InsightsTab } from './InsightsTab'
import { 
  Satellite, 
  BarChart3, 
  Rocket, 
  PlayCircle,
  Activity,
  Lightbulb,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'

const tabs = [
  { id: 'satellites' as const, label: 'Satellites', icon: Satellite },
  { id: 'ops' as const, label: 'Ops', icon: Activity },
  { id: 'insights' as const, label: 'Insights', icon: Lightbulb },
  { id: 'analysis' as const, label: 'Analysis', icon: BarChart3 },
  { id: 'launches' as const, label: 'Launches', icon: Rocket },
  { id: 'simulation' as const, label: 'Sim', icon: PlayCircle },
]

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen, activeTab, setActiveTab } = useStore()

  return (
    <div className={`
      fixed right-0 top-0 h-full z-20 flex transition-transform duration-300
      ${sidebarOpen ? 'translate-x-0' : 'translate-x-[calc(100%-48px)]'}
    `}>
      {/* Toggle button - larger on mobile */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="self-center -ml-10 w-10 h-16 md:w-8 md:h-14 md:-ml-8 bg-spacex-card hover:bg-spacex-border rounded-l-xl flex items-center justify-center transition"
      >
        {sidebarOpen ? <ChevronRight size={22} className="md:w-5 md:h-5" /> : <ChevronLeft size={22} className="md:w-5 md:h-5" />}
      </button>

      {/* Sidebar content */}
      <div className="w-80 md:w-96 h-full bg-spacex-card/95 backdrop-blur-lg border-l border-spacex-border flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-spacex-border">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex-1 py-3 px-2 flex flex-col items-center gap-1 transition
                ${activeTab === tab.id 
                  ? 'bg-spacex-accent/20 text-spacex-accent border-b-2 border-spacex-accent' 
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
                }
              `}
            >
              <tab.icon size={18} />
              <span className="text-xs">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'satellites' && <SatellitesTab />}
          {activeTab === 'ops' && <OpsTab />}
          {activeTab === 'insights' && <InsightsTab />}
          {activeTab === 'analysis' && <AnalysisTab />}
          {activeTab === 'launches' && <LaunchesTab />}
          {activeTab === 'simulation' && <SimulationTab />}
        </div>
      </div>
    </div>
  )
}
