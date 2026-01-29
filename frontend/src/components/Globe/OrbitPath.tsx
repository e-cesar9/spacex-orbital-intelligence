import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '@/stores/useStore'
import { getSatelliteOrbit } from '@/services/api'

const EARTH_RADIUS = 6.371
const SCALE_FACTOR = EARTH_RADIUS / 6371

interface OrbitPoint {
  t: string
  lat: number
  lon: number
  alt: number
}

export function OrbitPath() {
  const { selectedSatelliteId, showOrbits } = useStore()
  const markerRef = useRef<THREE.Mesh>(null)
  
  // Fetch orbit data when satellite is selected
  const { data: orbitData } = useQuery({
    queryKey: ['orbit', selectedSatelliteId],
    queryFn: () => getSatelliteOrbit(selectedSatelliteId!, 2, 2), // 2 hours, 2min steps
    enabled: !!selectedSatelliteId && showOrbits,
    staleTime: 60000,
  })

  // Convert orbit points to 3D coordinates
  const orbitPoints = useMemo(() => {
    if (!orbitData?.orbit) return []
    
    return orbitData.orbit.map((point: OrbitPoint) => {
      const phi = (90 - point.lat) * (Math.PI / 180)
      const theta = (point.lon + 180) * (Math.PI / 180)
      const r = EARTH_RADIUS + point.alt * SCALE_FACTOR * 0.001

      return new THREE.Vector3(
        -r * Math.sin(phi) * Math.cos(theta),
        r * Math.cos(phi),
        r * Math.sin(phi) * Math.sin(theta)
      )
    })
  }, [orbitData])

  // Animate marker along orbit
  const progressRef = useRef(0)
  useFrame((_, delta) => {
    if (markerRef.current && orbitPoints.length > 1) {
      progressRef.current = (progressRef.current + delta * 0.1) % 1
      const index = Math.floor(progressRef.current * (orbitPoints.length - 1))
      const nextIndex = Math.min(index + 1, orbitPoints.length - 1)
      const t = (progressRef.current * (orbitPoints.length - 1)) % 1
      
      const pos = orbitPoints[index].clone().lerp(orbitPoints[nextIndex], t)
      markerRef.current.position.copy(pos)
    }
  })

  if (!selectedSatelliteId || !showOrbits || orbitPoints.length < 2) return null

  return (
    <group>
      {/* Orbit path line */}
      <Line
        points={orbitPoints}
        color="#3b82f6"
        lineWidth={2}
        transparent
        opacity={0.6}
        dashed
        dashSize={0.1}
        gapSize={0.05}
      />
      
      {/* Future position marker */}
      <mesh ref={markerRef}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color="#22c55e" />
      </mesh>
      
      {/* Ground track (projected path on Earth surface) */}
      <GroundTrack orbit={orbitData?.orbit || []} />
    </group>
  )
}

function GroundTrack({ orbit }: { orbit: OrbitPoint[] }) {
  const groundPoints = useMemo(() => {
    return orbit.map((point) => {
      const phi = (90 - point.lat) * (Math.PI / 180)
      const theta = (point.lon + 180) * (Math.PI / 180)
      const r = EARTH_RADIUS * 1.001 // Just above Earth surface

      return new THREE.Vector3(
        -r * Math.sin(phi) * Math.cos(theta),
        r * Math.cos(phi),
        r * Math.sin(phi) * Math.sin(theta)
      )
    })
  }, [orbit])

  if (groundPoints.length < 2) return null

  return (
    <Line
      points={groundPoints}
      color="#f59e0b"
      lineWidth={1}
      transparent
      opacity={0.4}
    />
  )
}
