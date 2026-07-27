import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { computeHighlightsFromSteps } from '../utils/highlights'

/**
 * Playback + highlight state for backend algorithm step arrays.
 *
 * @param {object} options
 * @param {Array<object>} options.steps
 * @param {Array} options.graphEdges
 * @param {boolean} options.directed
 */
export default function useAlgorithmAnimation({
  steps = [],
  graphEdges = [],
  directed = false,
} = {}) {
  const [index, setIndex] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1) // 0.25x – 4x
  const stepsRef = useRef(steps)
  stepsRef.current = steps

  const total = steps.length

  // Reset when a new steps array arrives.
  useEffect(() => {
    setIndex(steps.length ? 0 : -1)
    setPlaying(false)
  }, [steps])

  const stepForward = useCallback(() => {
    setIndex((i) => {
      const next = Math.min((i < 0 ? -1 : i) + 1, stepsRef.current.length - 1)
      return next
    })
  }, [])

  const stepBack = useCallback(() => {
    setIndex((i) => Math.max(i - 1, stepsRef.current.length ? 0 : -1))
  }, [])

  const reset = useCallback(() => {
    setPlaying(false)
    setIndex(stepsRef.current.length ? 0 : -1)
  }, [])

  const goToEnd = useCallback(() => {
    setPlaying(false)
    setIndex(stepsRef.current.length ? stepsRef.current.length - 1 : -1)
  }, [])

  const play = useCallback(() => setPlaying(true), [])
  const pause = useCallback(() => setPlaying(false), [])
  const toggle = useCallback(() => setPlaying((p) => !p), [])

  // Autoplay ticker.
  useEffect(() => {
    if (!playing || total === 0) return undefined
    const delay = Math.max(80, 650 / speed)
    const id = setInterval(() => {
      setIndex((i) => {
        if (i >= stepsRef.current.length - 1) {
          setPlaying(false)
          return i
        }
        return i + 1
      })
    }, delay)
    return () => clearInterval(id)
  }, [playing, speed, total])

  const highlights = useMemo(() => {
    if (!total || index < 0) {
      return {
        nodeHighlightRoles: {},
        edgeHighlightRoles: {},
        highlightedNodes: new Set(),
        highlightedEdges: new Set(),
      }
    }
    return computeHighlightsFromSteps(steps, index, graphEdges, directed)
  }, [steps, index, total, graphEdges, directed])

  const currentStep = index >= 0 && index < total ? steps[index] : null
  const atEnd = total > 0 && index >= total - 1

  return {
    index,
    total,
    currentStep,
    playing,
    speed,
    setSpeed,
    stepForward,
    stepBack,
    reset,
    goToEnd,
    play,
    pause,
    toggle,
    atEnd,
    ...highlights,
  }
}
