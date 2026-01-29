import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '@/stores/useStore'
import type { WSMessage } from '@/types'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/positions`

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const { updateSatellites, setWsConnected, setSelectedSatelliteDetail, selectedSatelliteId } = useStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    console.log('Connecting to WebSocket...')
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setWsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)

        switch (message.type) {
          case 'positions':
            updateSatellites(message.data)
            break
          case 'satellite':
            if (message.data.satellite_id === selectedSatelliteId) {
              setSelectedSatelliteDetail(message.data)
            }
            break
          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }))
            break
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setWsConnected(false)
      wsRef.current = null

      // Reconnect after delay
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current = ws
  }, [updateSatellites, setWsConnected, setSelectedSatelliteDetail, selectedSatelliteId])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const subscribeSatellite = useCallback((satelliteId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        satellite_id: satelliteId
      }))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  // Subscribe to selected satellite
  useEffect(() => {
    if (selectedSatelliteId) {
      subscribeSatellite(selectedSatelliteId)
    }
  }, [selectedSatelliteId, subscribeSatellite])

  return {
    connected: wsRef.current?.readyState === WebSocket.OPEN,
    connect,
    disconnect,
    subscribeSatellite
  }
}
