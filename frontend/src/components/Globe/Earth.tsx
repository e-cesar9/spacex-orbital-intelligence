import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Sphere } from '@react-three/drei'
import * as THREE from 'three'
import { useStore } from '@/stores/useStore'

const EARTH_RADIUS = 6.371 // Scaled radius

export function Earth() {
  const meshRef = useRef<THREE.Mesh>(null)
  const cloudsRef = useRef<THREE.Mesh>(null)
  const { autoRotate } = useStore()

  // Generate procedural Earth texture
  const earthMaterial = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color(0x1a3a5c),
      emissive: new THREE.Color(0x0a1a2a),
      emissiveIntensity: 0.1,
      roughness: 0.8,
      metalness: 0.1,
    })
  }, [])

  // Atmosphere glow
  const atmosphereMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        glowColor: { value: new THREE.Color(0x4fc3dc) },
        viewVector: { value: new THREE.Vector3(0, 0, 1) },
      },
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 glowColor;
        varying vec3 vNormal;
        void main() {
          float intensity = pow(0.6 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
          gl_FragColor = vec4(glowColor, intensity * 0.5);
        }
      `,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
    })
  }, [])

  useFrame((_, delta) => {
    if (autoRotate && meshRef.current) {
      meshRef.current.rotation.y += delta * 0.05
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.02
    }
  })

  return (
    <group>
      {/* Earth */}
      <Sphere ref={meshRef} args={[EARTH_RADIUS, 64, 64]}>
        <primitive object={earthMaterial} attach="material" />
      </Sphere>

      {/* Grid lines (latitude/longitude) */}
      <GridLines radius={EARTH_RADIUS} />

      {/* Atmosphere */}
      <Sphere args={[EARTH_RADIUS * 1.05, 32, 32]}>
        <primitive object={atmosphereMaterial} attach="material" />
      </Sphere>
    </group>
  )
}

function GridLines({ radius }: { radius: number }) {
  const lines = useMemo(() => {
    const group = new THREE.Group()
    const material = new THREE.LineBasicMaterial({ 
      color: 0x3b82f6, 
      transparent: true, 
      opacity: 0.2 
    })

    // Latitude lines
    for (let lat = -60; lat <= 60; lat += 30) {
      const phi = (90 - lat) * (Math.PI / 180)
      const r = radius * Math.sin(phi)
      const y = radius * Math.cos(phi)
      
      const points = []
      for (let lon = 0; lon <= 360; lon += 5) {
        const theta = lon * (Math.PI / 180)
        points.push(new THREE.Vector3(
          r * Math.cos(theta),
          y,
          r * Math.sin(theta)
        ))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.Line(geometry, material)
      group.add(line)
    }

    // Longitude lines
    for (let lon = 0; lon < 360; lon += 30) {
      const points = []
      for (let lat = -90; lat <= 90; lat += 5) {
        const phi = (90 - lat) * (Math.PI / 180)
        const theta = lon * (Math.PI / 180)
        points.push(new THREE.Vector3(
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta)
        ))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.Line(geometry, material)
      group.add(line)
    }

    return group
  }, [radius])

  return <primitive object={lines} />
}
