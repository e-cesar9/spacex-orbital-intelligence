import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars, PerspectiveCamera } from '@react-three/drei'
import { Earth } from './Earth'
import { Satellites, SelectedSatelliteHighlight } from './Satellites'
import { OrbitPath } from './OrbitPath'
import { useStore } from '@/stores/useStore'

export function Globe() {
  const { satellites, autoRotate } = useStore()

  return (
    <div className="canvas-container w-full h-full">
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 20]} fov={45} />
        
        {/* Lighting */}
        <ambientLight intensity={0.3} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.3} />
        
        {/* Stars background */}
        <Stars 
          radius={100} 
          depth={50} 
          count={5000} 
          factor={4} 
          saturation={0} 
          fade 
          speed={1}
        />

        <Suspense fallback={null}>
          {/* Earth */}
          <Earth />
          
          {/* Satellites */}
          <Satellites positions={satellites} />
          
          {/* Selected satellite highlight */}
          <SelectedSatelliteHighlight />
          
          {/* Orbital path visualization */}
          <OrbitPath />
        </Suspense>

        {/* Controls */}
        <OrbitControls 
          ref={(controls) => {
            if (controls) {
              // @ts-ignore - store ref for zoom buttons
              window.__orbitControls = controls
            }
          }}
          enablePan={false}
          minDistance={8}
          maxDistance={50}
          autoRotate={autoRotate}
          autoRotateSpeed={0.5}
        />
      </Canvas>

      {/* Overlay UI */}
      <GlobeOverlay />
    </div>
  )
}

function GlobeOverlay() {
  const { wsConnected, lastUpdate, stats } = useStore()

  const handleZoom = (delta: number) => {
    // @ts-ignore
    const controls = window.__orbitControls
    if (controls) {
      const camera = controls.object
      const currentDistance = camera.position.length()
      const newDistance = Math.max(8, Math.min(50, currentDistance + delta))
      camera.position.setLength(newDistance)
      controls.update()
    }
  }

  return (
    <>
      {/* Connection status */}
      <div className="absolute top-4 left-4">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full glass ${
          wsConnected ? 'text-green-400' : 'text-red-400'
        }`}>
          <span className={`w-2 h-2 rounded-full ${
            wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
          }`} />
          <span className="text-sm">
            {wsConnected ? 'Live' : 'Connecting...'}
          </span>
        </div>
      </div>

      {/* Zoom controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-1">
        <button
          onClick={() => handleZoom(-3)}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center text-xl font-bold hover:bg-white/10 transition"
        >
          +
        </button>
        <button
          onClick={() => handleZoom(3)}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center text-xl font-bold hover:bg-white/10 transition"
        >
          −
        </button>
      </div>

      {/* Stats overlay */}
      <div className="absolute bottom-4 left-4 glass rounded-xl p-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-400 text-xs">Satellites</div>
            <div className="text-2xl font-bold text-blue-400">
              {stats.totalSatellites.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">Avg Altitude</div>
            <div className="text-2xl font-bold text-green-400">
              {stats.averageAltitude} km
            </div>
          </div>
        </div>
        {lastUpdate && (
          <div className="text-xs text-gray-500 mt-2">
            Updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 glass rounded-xl p-3">
        <div className="text-xs text-gray-400 mb-2 font-medium">Altitude Legend</div>
        <div className="flex flex-col gap-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]" />
            <span className="text-gray-300">&lt; 400 km <span className="text-gray-500">(Low LEO)</span></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500 shadow-[0_0_6px_rgba(59,130,246,0.5)]" />
            <span className="text-gray-300">400-600 km <span className="text-gray-500">(Starlink)</span></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-yellow-500 shadow-[0_0_6px_rgba(234,179,8,0.5)]" />
            <span className="text-gray-300">600-800 km <span className="text-gray-500">(High LEO)</span></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className="text-gray-300">&gt; 800 km <span className="text-gray-500">(Upper)</span></span>
          </div>
        </div>
        <div className="mt-2 pt-2 border-t border-white/10">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-3 h-3 rounded-full bg-red-400 ring-2 ring-red-400/50" />
            <span className="text-gray-300">Selected</span>
          </div>
        </div>
      </div>
    </>
  )
}
