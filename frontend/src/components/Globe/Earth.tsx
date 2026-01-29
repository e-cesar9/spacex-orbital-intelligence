import { useRef, useMemo } from 'react'
import { useFrame, useLoader } from '@react-three/fiber'
import { Sphere } from '@react-three/drei'
import * as THREE from 'three'
import { useStore } from '@/stores/useStore'

const EARTH_RADIUS = 6.371 // Scaled radius

// NASA Blue Marble texture URLs
const EARTH_TEXTURE_URL = 'https://unpkg.com/three-globe@2.31.1/example/img/earth-blue-marble.jpg'
const EARTH_NIGHT_URL = 'https://unpkg.com/three-globe@2.31.1/example/img/earth-night.jpg'
const EARTH_BUMP_URL = 'https://unpkg.com/three-globe@2.31.1/example/img/earth-topology.png'

export function Earth() {
  const meshRef = useRef<THREE.Mesh>(null)
  const { autoRotate, showEarthTexture } = useStore()

  // Load NASA textures
  const [earthTexture, nightTexture, bumpTexture] = useLoader(THREE.TextureLoader, [
    EARTH_TEXTURE_URL,
    EARTH_NIGHT_URL,
    EARTH_BUMP_URL
  ])

  // Configure textures
  useMemo(() => {
    if (earthTexture) {
      earthTexture.colorSpace = THREE.SRGBColorSpace
    }
    if (nightTexture) {
      nightTexture.colorSpace = THREE.SRGBColorSpace
    }
  }, [earthTexture, nightTexture])

  // Atmosphere glow
  const atmosphereMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        glowColor: { value: new THREE.Color(0x4fc3dc) },
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
  })

  return (
    <group>
      {/* Earth with NASA texture or solid color */}
      <Sphere ref={meshRef} args={[EARTH_RADIUS, 64, 64]}>
        {showEarthTexture ? (
          <meshStandardMaterial
            map={earthTexture}
            bumpMap={bumpTexture}
            bumpScale={0.05}
            roughness={0.8}
            metalness={0.1}
          />
        ) : (
          <meshStandardMaterial
            color={0x1a2744}
            roughness={0.9}
            metalness={0.1}
          />
        )}
      </Sphere>

      {/* Coordinate grid overlay */}
      <CoordinateGrid radius={EARTH_RADIUS * 1.002} />

      {/* Major cities/landmarks markers */}
      <LandmarkMarkers radius={EARTH_RADIUS} />

      {/* Atmosphere */}
      <Sphere args={[EARTH_RADIUS * 1.05, 32, 32]}>
        <primitive object={atmosphereMaterial} attach="material" />
      </Sphere>
    </group>
  )
}

function CoordinateGrid({ radius }: { radius: number }) {
  const lines = useMemo(() => {
    const group = new THREE.Group()
    const material = new THREE.LineBasicMaterial({ 
      color: 0x3b82f6, 
      transparent: true, 
      opacity: 0.15
    })
    
    const majorMaterial = new THREE.LineBasicMaterial({ 
      color: 0x60a5fa, 
      transparent: true, 
      opacity: 0.3
    })

    // Latitude lines
    for (let lat = -80; lat <= 80; lat += 20) {
      const isMajor = lat === 0 || lat === 60 || lat === -60
      const phi = (90 - lat) * (Math.PI / 180)
      const r = radius * Math.sin(phi)
      const y = radius * Math.cos(phi)
      
      const points = []
      for (let lon = 0; lon <= 360; lon += 3) {
        const theta = lon * (Math.PI / 180)
        points.push(new THREE.Vector3(
          r * Math.cos(theta),
          y,
          r * Math.sin(theta)
        ))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.Line(geometry, isMajor ? majorMaterial : material)
      group.add(line)
    }

    // Longitude lines
    for (let lon = 0; lon < 360; lon += 30) {
      const isMajor = lon === 0 || lon === 180
      const points = []
      for (let lat = -90; lat <= 90; lat += 3) {
        const phi = (90 - lat) * (Math.PI / 180)
        const theta = lon * (Math.PI / 180)
        points.push(new THREE.Vector3(
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta)
        ))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.Line(geometry, isMajor ? majorMaterial : material)
      group.add(line)
    }

    return group
  }, [radius])

  return <primitive object={lines} />
}

// Ground stations for satellite communication
const GROUND_STATIONS = [
  { name: 'Svalbard', lat: 78.23, lon: 15.39, color: 0x06b6d4 },
  { name: 'Alaska', lat: 64.86, lon: -147.85, color: 0x06b6d4 },
  { name: 'McMurdo', lat: -77.85, lon: 166.67, color: 0x06b6d4 },
  { name: 'Punta Arenas', lat: -53.16, lon: -70.91, color: 0x06b6d4 },
  { name: 'Hawaii', lat: 20.71, lon: -156.26, color: 0x06b6d4 },
  { name: 'Guam', lat: 13.44, lon: 144.79, color: 0x06b6d4 },
]

// SpaceX facilities
const SPACEX_FACILITIES = [
  { name: 'Cape Canaveral', lat: 28.5, lon: -80.6, color: 0x22c55e },
  { name: 'Vandenberg', lat: 34.7, lon: -120.5, color: 0x22c55e },
  { name: 'Starbase', lat: 25.99, lon: -97.15, color: 0xf59e0b },
  { name: 'SpaceX HQ', lat: 33.92, lon: -118.33, color: 0x3b82f6 },
]

const LANDMARKS = [...GROUND_STATIONS, ...SPACEX_FACILITIES]

function LandmarkMarkers({ radius }: { radius: number }) {
  return (
    <group>
      {LANDMARKS.map((landmark) => {
        const phi = (90 - landmark.lat) * (Math.PI / 180)
        const theta = (landmark.lon + 180) * (Math.PI / 180)
        const r = radius * 1.005

        const x = -r * Math.sin(phi) * Math.cos(theta)
        const y = r * Math.cos(phi)
        const z = r * Math.sin(phi) * Math.sin(theta)

        return (
          <group key={landmark.name} position={[x, y, z]}>
            <mesh>
              <sphereGeometry args={[0.03, 8, 8]} />
              <meshBasicMaterial color={landmark.color} />
            </mesh>
          </group>
        )
      })}
    </group>
  )
}
