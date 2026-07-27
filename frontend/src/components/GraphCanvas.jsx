import { useEffect, useMemo, useRef } from 'react'
import { DataSet, Network } from 'vis-network/standalone'
import './GraphCanvas.css'

const COLORS = {
  node: '#4a6fa5',
  nodeBorder: '#9eb6d4',
  nodeText: '#f2f6fb',
  nodeHighlight: '#d4a84b',
  nodeHighlightBorder: '#f0d9a0',
  edge: '#8aa0b8',
  edgeText: '#c5d2e0',
  edgeHighlight: '#e0b84e',
}

/**
 * Vis-network canvas for interactive graph rendering.
 *
 * @param {{
 *   nodes: Array<{id: string|number, label?: string, x?: number, y?: number}>,
 *   edges: Array<{id?: string|number, from: string|number, to: string|number, weight?: number, directed?: boolean}>,
 *   highlightedNodes?: Iterable<string|number>|Set<string|number>,
 *   highlightedEdges?: Iterable<string|number>|Set<string|number>,
 *   directed?: boolean,
 *   weighted?: boolean,
 *   onNodeClick?: (nodeId: string|number) => void,
 *   onEdgeClick?: (edgeId: string|number) => void,
 * }} props
 */
export default function GraphCanvas({
  nodes = [],
  edges = [],
  highlightedNodes,
  highlightedEdges,
  directed = false,
  weighted = false,
  onNodeClick,
  onEdgeClick,
}) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const nodesDataRef = useRef(null)
  const edgesDataRef = useRef(null)
  const onNodeClickRef = useRef(onNodeClick)
  const onEdgeClickRef = useRef(onEdgeClick)

  onNodeClickRef.current = onNodeClick
  onEdgeClickRef.current = onEdgeClick

  const highlightNodeSet = useMemo(
    () => toIdSet(highlightedNodes),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(highlightedNodes ? [...highlightedNodes].map(String).sort() : [])],
  )
  const highlightEdgeSet = useMemo(
    () => toIdSet(highlightedEdges),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(highlightedEdges ? [...highlightedEdges].map(String).sort() : [])],
  )

  // Keep latest graph props in refs so StrictMode remount can re-hydrate.
  const graphRef = useRef({
    nodes,
    edges,
    directed,
    weighted,
    highlightNodeSet,
    highlightEdgeSet,
  })
  graphRef.current = {
    nodes,
    edges,
    directed,
    weighted,
    highlightNodeSet,
    highlightEdgeSet,
  }

  const applyGraphToNetwork = (payload) => {
    if (!nodesDataRef.current || !edgesDataRef.current || !networkRef.current) {
      return
    }

    const {
      nodes: nextNodes,
      edges: nextEdges,
      directed: isDirected,
      weighted: isWeighted,
      highlightNodeSet: hiNodes,
      highlightEdgeSet: hiEdges,
    } = payload

    const visNodes = nextNodes.map((n) => {
      const id = n.id
      const isHi = hiNodes.has(String(id))
      const item = {
        id,
        label: n.label != null ? String(n.label) : String(id),
        color: isHi
          ? {
              background: COLORS.nodeHighlight,
              border: COLORS.nodeHighlightBorder,
              highlight: {
                background: COLORS.nodeHighlight,
                border: COLORS.nodeHighlightBorder,
              },
            }
          : {
              background: COLORS.node,
              border: COLORS.nodeBorder,
              highlight: {
                background: COLORS.nodeHighlight,
                border: COLORS.nodeHighlightBorder,
              },
              hover: {
                background: '#5d82b8',
                border: '#c5d4e8',
              },
            },
      }
      if (typeof n.x === 'number') item.x = n.x
      if (typeof n.y === 'number') item.y = n.y
      return item
    })

    const nodeIds = new Set(visNodes.map((n) => n.id))
    const visEdges = nextEdges
      .filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
      .map((e, index) => {
        const id = e.id != null ? e.id : `e-${e.from}-${e.to}-${index}`
        const edgeDirected = e.directed != null ? Boolean(e.directed) : isDirected
        const showWeight = isWeighted || e.weight != null
        const isHi = hiEdges.has(String(id))
        return {
          id,
          from: e.from,
          to: e.to,
          label: showWeight && e.weight != null ? formatWeight(e.weight) : undefined,
          arrows: edgeDirected
            ? { to: { enabled: true, scaleFactor: 0.7 } }
            : undefined,
          color: isHi
            ? {
                color: COLORS.edgeHighlight,
                highlight: COLORS.edgeHighlight,
                hover: COLORS.edgeHighlight,
              }
            : {
                color: COLORS.edge,
                highlight: COLORS.edgeHighlight,
                hover: '#a8bdd4',
              },
          width: isHi ? 2.8 : 1.8,
        }
      })

    // Debug: verify payload shape right before DataSet write.
    console.log('[GraphCanvas] applying to vis-network', {
      nodeCount: visNodes.length,
      edgeCount: visEdges.length,
      nodes: visNodes,
      edges: visEdges,
      containerSize: containerRef.current
        ? {
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight,
          }
        : null,
    })

    nodesDataRef.current.clear()
    edgesDataRef.current.clear()
    if (visNodes.length) nodesDataRef.current.add(visNodes)
    if (visEdges.length) edgesDataRef.current.add(visEdges)

    const network = networkRef.current
    const width = containerRef.current?.clientWidth || 800
    const height = Math.max(containerRef.current?.clientHeight || 0, 600)
    network.setSize(`${width}px`, `${height}px`)
    network.redraw()

    if (visNodes.length > 0) {
      network.stabilize(100)
      network.once('stabilizationIterationsDone', () => {
        network.fit({
          animation: { duration: 250, easingFunction: 'easeInOutQuad' },
        })
      })
    }
  }

  // Create Network once (re-create safely under React StrictMode).
  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    nodesDataRef.current = new DataSet([])
    edgesDataRef.current = new DataSet([])

    console.log('[GraphCanvas] creating Network instance')
    networkRef.current = new Network(
      container,
      {
        nodes: nodesDataRef.current,
        edges: edgesDataRef.current,
      },
      {
        autoResize: true,
        clickToUse: false,
        interaction: {
          hover: true,
          tooltipDelay: 120,
          navigationButtons: false,
          keyboard: false,
          dragNodes: true,
          dragView: true,
          zoomView: true,
        },
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -48,
            centralGravity: 0.01,
            springLength: 120,
            springConstant: 0.07,
            avoidOverlap: 0.5,
          },
          stabilization: { iterations: 120, fit: true },
        },
        nodes: {
          shape: 'dot',
          size: 18,
          font: {
            face: 'IBM Plex Sans, Segoe UI, sans-serif',
            size: 14,
            color: COLORS.nodeText,
            strokeWidth: 0,
          },
          borderWidth: 2,
          shadow: false,
        },
        edges: {
          width: 1.8,
          font: {
            face: 'IBM Plex Mono, ui-monospace, monospace',
            size: 11,
            color: COLORS.edgeText,
            strokeWidth: 0,
            align: 'middle',
          },
          smooth: {
            enabled: true,
            type: 'dynamic',
            roundness: 0.3,
          },
          selectionWidth: 2.5,
        },
      },
    )

    const onClick = (params) => {
      if (params.nodes?.length && onNodeClickRef.current) {
        onNodeClickRef.current(params.nodes[0])
      } else if (params.edges?.length && onEdgeClickRef.current) {
        onEdgeClickRef.current(params.edges[0])
      }
    }
    networkRef.current.on('click', onClick)

    // Re-apply current props after create (covers StrictMode remount).
    applyGraphToNetwork(graphRef.current)

    // If layout was still settling, resize once more on next frame.
    const raf = requestAnimationFrame(() => {
      if (!networkRef.current || !containerRef.current) return
      const width = containerRef.current.clientWidth || 800
      const height = Math.max(containerRef.current.clientHeight || 0, 600)
      networkRef.current.setSize(`${width}px`, `${height}px`)
      networkRef.current.redraw()
      if (graphRef.current.nodes.length > 0) {
        networkRef.current.fit()
      }
    })

    return () => {
      cancelAnimationFrame(raf)
      networkRef.current?.off('click', onClick)
      networkRef.current?.destroy()
      networkRef.current = null
      nodesDataRef.current = null
      edgesDataRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sync whenever graph props change.
  useEffect(() => {
    applyGraphToNetwork({
      nodes,
      edges,
      directed,
      weighted,
      highlightNodeSet,
      highlightEdgeSet,
    })
  }, [nodes, edges, directed, weighted, highlightNodeSet, highlightEdgeSet])

  return (
    <div className="graph-canvas">
      <div ref={containerRef} className="graph-canvas__viewport" />
      {nodes.length === 0 && (
        <div className="graph-canvas__empty">
          <p>No graph loaded</p>
          <span>Generate, load a preset, or add nodes manually.</span>
        </div>
      )}
    </div>
  )
}

function toIdSet(value) {
  if (!value) return new Set()
  if (value instanceof Set) {
    return new Set([...value].map(String))
  }
  return new Set([...value].map(String))
}

function formatWeight(weight) {
  const n = Number(weight)
  if (!Number.isFinite(n)) return String(weight)
  return Number.isInteger(n) ? String(n) : n.toFixed(2)
}
