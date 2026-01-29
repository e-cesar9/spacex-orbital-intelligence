import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars, PerspectiveCamera } from '@react-three/drei'
import { Earth } from './Earth'
import { Satellites, SelectedSatelliteHighlight } from './Satellites'
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
        </Suspense>

        {/* Controls */}
        <OrbitControls 
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

      {/* Stats overlay */}
      <div className="absolute bottom-4 left-4 glass rounded-xl p-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-400">Satellites</div>
            <div className="text-2xl font-bold text-blue-400">
              {stats.totalSatellites.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Avg Altitude</div>
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
        <div className="text-xs text-gray-400 mb-2">Altitude</div>
        <div className="flex flex-col gap-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span>&lt; 400 km</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500" />
            <span>400-600 km</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span>600-800 km</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span>&gt; 800 km</span>
          </div>
        </div>
      </div>
    </>
  )
}
