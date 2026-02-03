import { useMemo } from 'react'
import type { EQSettings } from '../types'

interface EQVisualizerProps {
  settings: EQSettings
  width?: number
  height?: number
}

export default function EQVisualizer({ settings, width = 400, height = 200 }: EQVisualizerProps) {
  const path = useMemo(() => {
    const points: string[] = []
    const numPoints = 100
    const minFreq = 20
    const maxFreq = 20000
    const dbRange = 24 // ±12dB

    for (let i = 0; i <= numPoints; i++) {
      const freq = minFreq * Math.pow(maxFreq / minFreq, i / numPoints)
      const x = (Math.log10(freq / minFreq) / Math.log10(maxFreq / minFreq)) * width

      let totalGain = 0

      // HPF contribution
      if (settings.hpf_enabled) {
        const hpfFreq = settings.hpf_frequency
        if (freq < hpfFreq) {
          totalGain -= 12 * Math.log2(hpfFreq / freq)
        }
      }

      // Band contributions
      const bands = [
        { ...settings.low, type: settings.low.type || 'shelf' },
        { ...settings.low_mid, type: 'peak' },
        { ...settings.high_mid, type: 'peak' },
        { ...settings.high, type: settings.high.type || 'shelf' },
      ]

      bands.forEach((band) => {
        const bandFreq = band.frequency
        const gain = band.gain
        const q = band.q

        if (band.type === 'shelf') {
          // Simplified shelf calculation
          const ratio = freq / bandFreq
          if (bandFreq < 500) {
            // Low shelf
            totalGain += gain / (1 + Math.pow(ratio, 2))
          } else {
            // High shelf
            totalGain += gain * Math.pow(ratio, 2) / (1 + Math.pow(ratio, 2))
          }
        } else {
          // Peak/bell filter
          const w = freq / bandFreq
          const bw = 1 / q
          const response = gain / (1 + Math.pow((w - 1 / w) / bw, 2))
          totalGain += response
        }
      })

      // Clamp gain
      totalGain = Math.max(-12, Math.min(12, totalGain))

      // Convert dB to Y position
      const y = height / 2 - (totalGain / dbRange) * height

      if (i === 0) {
        points.push(`M ${x} ${y}`)
      } else {
        points.push(`L ${x} ${y}`)
      }
    }

    return points.join(' ')
  }, [settings, width, height])

  // Frequency markers
  const freqMarkers = [100, 1000, 10000]

  return (
    <div className="bg-gray-900 rounded-lg p-2">
      <svg width={width} height={height} className="overflow-visible">
        {/* Grid */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#333" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#grid)" />

        {/* 0dB line */}
        <line
          x1={0}
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="#666"
          strokeWidth="1"
        />

        {/* Frequency markers */}
        {freqMarkers.map((freq) => {
          const x = (Math.log10(freq / 20) / Math.log10(20000 / 20)) * width
          return (
            <g key={freq}>
              <line
                x1={x}
                y1={0}
                x2={x}
                y2={height}
                stroke="#444"
                strokeWidth="1"
                strokeDasharray="4"
              />
              <text
                x={x}
                y={height - 5}
                fill="#666"
                fontSize="10"
                textAnchor="middle"
              >
                {freq >= 1000 ? `${freq / 1000}k` : freq}
              </text>
            </g>
          )
        })}

        {/* EQ curve */}
        <path
          d={path}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
        />

        {/* Band handles */}
        {[settings.low, settings.low_mid, settings.high_mid, settings.high].map((band, i) => {
          const x = (Math.log10(band.frequency / 20) / Math.log10(20000 / 20)) * width
          const y = height / 2 - (band.gain / 24) * height
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={6}
              fill="#3b82f6"
              stroke="#fff"
              strokeWidth="2"
              className="cursor-pointer"
            />
          )
        })}
      </svg>

      {/* Legend */}
      <div className="flex justify-between mt-2 text-xs text-gray-400">
        <span>20 Hz</span>
        <span>1 kHz</span>
        <span>20 kHz</span>
      </div>
    </div>
  )
}
