import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars, PerspectiveCamera } from '@react-three/drei'
import { Earth } from './Earth'
import { Satellites, SelectedSatelliteHighlight } from './Satellites'
import { OrbitPath } from './OrbitPath'
import { useStore } from '@/stores/useStore'
import { Maximize2, Minimize2 } from 'lucide-react'

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
  const { lastUpdate, stats, isFullscreen, toggleFullscreen } = useStore()
  
  // Listen for fullscreen changes (ESC key, etc.)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement
      if (isNowFullscreen !== useStore.getState().isFullscreen) {
        useStore.setState({ 
          isFullscreen: isNowFullscreen,
          sidebarOpen: !isNowFullscreen
        })
      }
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

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

  // Format number in scientific notation
  const formatScientific = (num: number) => {
    if (num === 0) return '0'
    const exp = Math.floor(Math.log10(Math.abs(num)))
    const mantissa = (num / Math.pow(10, exp)).toFixed(2)
    const superscript = exp.toString().split('').map(c => 
      c === '-' ? '⁻' : '⁰¹²³⁴⁵⁶⁷⁸⁹'[parseInt(c)]
    ).join('')
    return `${mantissa} × 10${superscript}`
  }

  return (
    <>
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
        <button
          onClick={toggleFullscreen}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center hover:bg-white/10 transition mt-2"
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>
      </div>

      {/* Stats overlay - Left side */}
      <div className="absolute bottom-4 left-4">
        {/* Time - Above the box */}
        {lastUpdate && (
          <div className="text-[10px] text-gray-600 mb-2 font-mono">
            {lastUpdate.toLocaleTimeString()}
          </div>
        )}
        
        <div className="glass rounded-xl p-4">
          {/* Altitude Legend */}
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Altitude Legend</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-gray-400">&lt;400km</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span className="text-gray-400">400-600</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-gray-400">600-800</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-gray-400">&gt;800km</span>
            </div>
          </div>
          
          {/* Stats */}
          <div className="flex items-start gap-6 mt-3 pt-3 border-t border-white/10">
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Satellites</div>
              <div className="text-xl font-bold text-blue-400 font-mono">
                {stats.totalSatellites.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Avg Alt</div>
              <div className="text-sm font-bold text-green-400 font-mono">
                ≈ {formatScientific(stats.averageAltitude)} km
              </div>
              <div className="text-sm font-bold text-gray-400 font-mono">
                {formatScientific(stats.averageAltitude / 420 * 100)} %
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
