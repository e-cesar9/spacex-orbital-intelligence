import { useMemo, useRef } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
// useFrame still used in Satellites component
import * as THREE from 'three'
import { useStore } from '@/stores/useStore'
import type { SatellitePosition } from '@/types'

const EARTH_RADIUS = 6.371
const SCALE_FACTOR = EARTH_RADIUS / 6371 // Scale to our Earth

interface SatellitesProps {
  positions: SatellitePosition[]
}

export function Satellites({ positions }: SatellitesProps) {
  const { selectedSatelliteId, selectSatellite, altitudeRange } = useStore()
  const instancedMeshRef = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])

  // Filter by altitude
  const filteredPositions = useMemo(() => {
    return positions.filter(p => 
      p.alt >= altitudeRange[0] && p.alt <= altitudeRange[1]
    )
  }, [positions, altitudeRange])

  // Convert lat/lon/alt to 3D coordinates
  const satelliteData = useMemo(() => {
    return filteredPositions.map(sat => {
      const phi = (90 - sat.lat) * (Math.PI / 180)
      const theta = (sat.lon + 180) * (Math.PI / 180)
      const r = EARTH_RADIUS + sat.alt * SCALE_FACTOR * 0.001 // Scale altitude

      return {
        ...sat,
        x: -r * Math.sin(phi) * Math.cos(theta),
        y: r * Math.cos(phi),
        z: r * Math.sin(phi) * Math.sin(theta),
        selected: sat.id === selectedSatelliteId
      }
    })
  }, [filteredPositions, selectedSatelliteId])

  // Update instanced mesh
  useFrame(() => {
    if (!instancedMeshRef.current) return

    satelliteData.forEach((sat, i) => {
      dummy.position.set(sat.x, sat.y, sat.z)
      dummy.scale.setScalar(sat.selected ? 0.03 : 0.015)
      dummy.updateMatrix()
      instancedMeshRef.current!.setMatrixAt(i, dummy.matrix)

      // Color based on selection/altitude
      const color = sat.selected 
        ? new THREE.Color(0xff6b6b)
        : getAltitudeColor(sat.alt)
      instancedMeshRef.current!.setColorAt(i, color)
    })

    instancedMeshRef.current.instanceMatrix.needsUpdate = true
    if (instancedMeshRef.current.instanceColor) {
      instancedMeshRef.current.instanceColor.needsUpdate = true
    }
  })

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    const instanceId = event.instanceId
    if (instanceId !== undefined && satelliteData[instanceId]) {
      selectSatellite(satelliteData[instanceId].id)
    }
  }

  return (
    <instancedMesh
      ref={instancedMeshRef}
      args={[undefined, undefined, satelliteData.length]}
      onClick={handleClick}
    >
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial />
    </instancedMesh>
  )
}

// Selected satellite highlight - simple red dot
export function SelectedSatelliteHighlight() {
  const { selectedSatellite, satellites, selectedSatelliteId } = useStore()

  // Get position from satellites array if no detail loaded yet
  const satPos = selectedSatellite?.geographic || 
    (selectedSatelliteId ? satellites.find(s => s.id === selectedSatelliteId) : null)

  if (!satPos) return null

  const lat = 'latitude' in satPos ? satPos.latitude : satPos.lat
  const lon = 'longitude' in satPos ? satPos.longitude : satPos.lon
  const alt = 'altitude' in satPos ? satPos.altitude : satPos.alt

  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  const r = EARTH_RADIUS + alt * SCALE_FACTOR * 0.001

  const x = -r * Math.sin(phi) * Math.cos(theta)
  const y = r * Math.cos(phi)
  const z = r * Math.sin(phi) * Math.sin(theta)

  return (
    <group position={[x, y, z]}>
      {/* Red dot */}
      <mesh>
        <sphereGeometry args={[0.03, 16, 16]} />
        <meshBasicMaterial color={0xff4444} />
      </mesh>
    </group>
  )
}

function getAltitudeColor(altitude: number): THREE.Color {
  // Color gradient based on altitude
  if (altitude < 400) return new THREE.Color(0x22c55e) // Green - Low LEO
  if (altitude < 600) return new THREE.Color(0x3b82f6) // Blue - Starlink range
  if (altitude < 800) return new THREE.Color(0xf59e0b) // Yellow - Higher LEO
  return new THREE.Color(0xef4444) // Red - High altitude
}
