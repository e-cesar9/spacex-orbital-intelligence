import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Globe } from '@/components/Globe'
import { Sidebar } from '@/components/Sidebar'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Rocket } from 'lucide-react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 2,
    },
  },
})

function AppContent() {
  // Initialize WebSocket connection
  useWebSocket()

  return (
    <div className="h-screen w-screen overflow-hidden bg-spacex-dark">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-20 pointer-events-none">
        <div className="p-4 pb-8 flex justify-between items-center">
          <div className="flex items-center gap-3 pointer-events-auto">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-spacex-accent to-blue-600 flex items-center justify-center shrink-0">
              <Rocket size={24} className="text-white" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold leading-tight">SpaceX Orbital Intelligence</h1>
                <span className="px-1.5 py-0.5 text-[9px] font-bold bg-yellow-500/20 text-yellow-400 rounded uppercase tracking-wider">
                  Demo
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">Real-time Starlink Constellation Tracking</p>
            </div>
          </div>
        </div>
      </header>

      {/* 3D Globe */}
      <main className="absolute inset-0">
        <Globe />
      </main>

      {/* Sidebar */}
      <Sidebar />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}
