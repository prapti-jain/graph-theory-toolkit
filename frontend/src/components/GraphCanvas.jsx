import { useEffect, useMemo, useRef } from 'react'
import { DataSet, Network } from 'vis-network/standalone'
import {
  EDGE_ROLE_COLORS,
  NODE_ROLE_COLORS,
} from '../utils/highlights'
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
 */
export default function GraphCanvas({
  nodes = [],
  edges = [],
  highlightedNodes,
  highlightedEdges,
  nodeHighlightRoles = {},
  edgeHighlightRoles = {},
  directed = false,
  weighted = false,
  onNodeClick,
  onEdgeClick,
}) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const nodesDataRef = useRef(null)
  const edgesDataRef = useRef(null)
  const structureKeyRef = useRef('')
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

  const rolesKey = useMemo(
    () =>
      JSON.stringify({
        n: nodeHighlightRoles,
        e: edgeHighlightRoles,
        hn: [...highlightNodeSet].sort(),
        he: [...highlightEdgeSet].sort(),
      }),
    [nodeHighlightRoles, edgeHighlightRoles, highlightNodeSet, highlightEdgeSet],
  )

  const structureKey = useMemo(
    () =>
      JSON.stringify({
        directed,
        weighted,
        nodes: nodes.map((n) => [n.id, n.label, n.x, n.y]),
        edges: edges.map((e) => [e.id, e.from, e.to, e.weight, e.directed]),
      }),
    [nodes, edges, directed, weighted],
  )

  const graphRef = useRef({})
  graphRef.current = {
    nodes,
    edges,
    directed,
    weighted,
    highlightNodeSet,
    highlightEdgeSet,
    nodeHighlightRoles,
    edgeHighlightRoles,
  }

  const buildVisNodes = (payload) => {
    const {
      nodes: nextNodes,
      highlightNodeSet: hiNodes,
      nodeHighlightRoles: roles,
    } = payload
    return nextNodes.map((n) => {
      const id = n.id
      const role = roles?.[String(id)]
      const isHi = Boolean(role) || hiNodes.has(String(id))
      const roleColor = role ? NODE_ROLE_COLORS[role] : null
      const item = {
        id,
        label: n.label != null ? String(n.label) : String(id),
        color: isHi
          ? {
              background: roleColor?.background || COLORS.nodeHighlight,
              border: roleColor?.border || COLORS.nodeHighlightBorder,
              highlight: {
                background: roleColor?.background || COLORS.nodeHighlight,
                border: roleColor?.border || COLORS.nodeHighlightBorder,
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
        borderWidth: role === 'current' ? 3 : 2,
        size: role === 'current' ? 22 : 18,
      }
      if (typeof n.x === 'number') item.x = n.x
      if (typeof n.y === 'number') item.y = n.y
      return item
    })
  }

  const buildVisEdges = (payload) => {
    const {
      edges: nextEdges,
      directed: isDirected,
      weighted: isWeighted,
      highlightEdgeSet: hiEdges,
      edgeHighlightRoles: roles,
      nodes: nextNodes,
    } = payload
    const nodeIds = new Set(nextNodes.map((n) => n.id))
    return nextEdges
      .filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
      .map((e, index) => {
        const id = e.id != null ? e.id : `e-${e.from}-${e.to}-${index}`
        const edgeDirected = e.directed != null ? Boolean(e.directed) : isDirected
        const showWeight = isWeighted || e.weight != null
        const role = roles?.[String(id)]
        const isHi = Boolean(role) || hiEdges.has(String(id))
        const roleStyle = role ? EDGE_ROLE_COLORS[role] : null
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
                color: roleStyle?.color || COLORS.edgeHighlight,
                highlight: roleStyle?.color || COLORS.edgeHighlight,
                hover: roleStyle?.color || COLORS.edgeHighlight,
              }
            : {
                color: COLORS.edge,
                highlight: COLORS.edgeHighlight,
                hover: '#a8bdd4',
              },
          width: isHi ? roleStyle?.width || 2.8 : 1.8,
        }
      })
  }

  const resizeNetwork = () => {
    if (!networkRef.current || !containerRef.current) return
    const width = containerRef.current.clientWidth || 800
    const height = Math.max(containerRef.current.clientHeight || 0, 600)
    networkRef.current.setSize(`${width}px`, `${height}px`)
    networkRef.current.redraw()
  }

  const applyStructure = (payload, { fit = true } = {}) => {
    if (!nodesDataRef.current || !edgesDataRef.current || !networkRef.current) return

    const visNodes = buildVisNodes(payload)
    const visEdges = buildVisEdges(payload)

    console.log('[GraphCanvas] structure update', {
      nodeCount: visNodes.length,
      edgeCount: visEdges.length,
      sampleNodes: visNodes.slice(0, 3),
      sampleEdges: visEdges.slice(0, 3),
      containerSize: {
        width: containerRef.current?.clientWidth,
        height: containerRef.current?.clientHeight,
      },
    })

    nodesDataRef.current.clear()
    edgesDataRef.current.clear()
    if (visNodes.length) nodesDataRef.current.add(visNodes)
    if (visEdges.length) edgesDataRef.current.add(visEdges)

    resizeNetwork()
    if (fit && visNodes.length > 0) {
      networkRef.current.stabilize(80)
      networkRef.current.once('stabilizationIterationsDone', () => {
        networkRef.current?.fit({
          animation: { duration: 220, easingFunction: 'easeInOutQuad' },
        })
      })
    }
  }

  const applyHighlightsOnly = (payload) => {
    if (!nodesDataRef.current || !edgesDataRef.current || !networkRef.current) return
    const visNodes = buildVisNodes(payload)
    const visEdges = buildVisEdges(payload)
    // Update in place — avoids layout jumps during animation.
    if (visNodes.length) nodesDataRef.current.update(visNodes)
    if (visEdges.length) edgesDataRef.current.update(visEdges)
    networkRef.current.redraw()
  }

  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    nodesDataRef.current = new DataSet([])
    edgesDataRef.current = new DataSet([])
    structureKeyRef.current = ''

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
          stabilization: { iterations: 100, fit: true },
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

    structureKeyRef.current = structureKey
    applyStructure(graphRef.current, { fit: true })

    const raf = requestAnimationFrame(() => {
      resizeNetwork()
      if (graphRef.current.nodes.length > 0) networkRef.current?.fit()
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

  // Structure changes (new graph) → full reload + layout.
  useEffect(() => {
    if (!networkRef.current) return
    if (structureKeyRef.current === structureKey) return
    structureKeyRef.current = structureKey
    applyStructure(graphRef.current, { fit: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structureKey])

  // Highlight-only changes → color updates, no re-layout.
  useEffect(() => {
    if (!networkRef.current) return
    applyHighlightsOnly(graphRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rolesKey])

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
  if (value instanceof Set) return new Set([...value].map(String))
  return new Set([...value].map(String))
}

function formatWeight(weight) {
  const n = Number(weight)
  if (!Number.isFinite(n)) return String(weight)
  return Number.isInteger(n) ? String(n) : n.toFixed(2)
}
