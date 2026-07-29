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

/** Radius range used when encoding centrality via vis-network `value` scaling. */
const SCORE_SIZE_MIN = 8
const SCORE_SIZE_MAX = 44

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
  nodeScores = null,
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

  const scoreNorm = useMemo(() => {
    const norm = normalizeScores(nodeScores)
    const isNullish = nodeScores == null
    const isObject = nodeScores != null && typeof nodeScores === 'object'
    const keyCount = isObject ? Object.keys(nodeScores).length : null
    const shape = isNullish
      ? nodeScores === null
        ? 'null'
        : 'undefined'
      : isObject
        ? keyCount === 0
          ? 'empty-object'
          : 'populated-object'
        : typeof nodeScores
    const sampleEntries = norm
      ? Object.entries(norm).slice(0, 3)
      : null
    // eslint-disable-next-line no-console
    console.log('[centrality-scale] GraphCanvas scoreNorm', {
      nodeScoresType: typeof nodeScores,
      nodeScoresShape: shape,
      nodeScoresKeyCount: keyCount,
      nodeScoresSample:
        isObject
          ? JSON.stringify(Object.fromEntries(Object.entries(nodeScores).slice(0, 5)))
          : String(nodeScores),
      scoreNormSize: norm ? Object.keys(norm).length : 0,
      scoreNormSample: sampleEntries,
      scoreNormIsNull: norm == null,
      sampleLookup: norm
        ? {
            asString33: lookupScore(norm, '33'),
            asNumber33: lookupScore(norm, 33),
          }
        : null,
    })
    return norm
  }, [nodeScores])
  const rawScores = useMemo(() => flattenScoreMap(nodeScores), [nodeScores])

  const scoresKey = useMemo(() => {
    if (!scoreNorm) return ''
    return Object.entries(scoreNorm)
      .sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }))
      .map(([k, v]) => `${k}:${v.toFixed(4)}`)
      .join('|')
  }, [scoreNorm])

  // Include scoresKey so highlight ticks never re-apply without current scores.
  const rolesKey = useMemo(
    () =>
      JSON.stringify({
        n: nodeHighlightRoles,
        e: edgeHighlightRoles,
        hn: [...highlightNodeSet].sort(),
        he: [...highlightEdgeSet].sort(),
        s: scoresKey,
      }),
    [nodeHighlightRoles, edgeHighlightRoles, highlightNodeSet, highlightEdgeSet, scoresKey],
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
    scoreNorm,
    rawScores,
  }

  const buildVisNodes = (payload, { logScores = false } = {}) => {
    const {
      nodes: nextNodes,
      highlightNodeSet: hiNodes,
      nodeHighlightRoles: roles,
      scoreNorm: scores,
      rawScores: raw,
    } = payload

    return nextNodes.map((n) => {
      const id = n.id
      const key = String(id)
      const role = roles?.[key] ?? roles?.[id]
      const t = lookupScore(scores, id)
      const hasScore = typeof t === 'number'
      const rawScore = lookupScore(raw, id)
      const scoreBg = hasScore ? scoreToColor(t) : null
      const scoreBorder = hasScore ? scoreToBorder(t) : null

      // vis-network encodes variable size via `value` + nodes.scaling
      // (per-node `size` is reset by setValueRange when value is absent).
      const value = hasScore ? t : undefined
      const size = hasScore
        ? SCORE_SIZE_MIN + t * (SCORE_SIZE_MAX - SCORE_SIZE_MIN)
        : role === 'current'
          ? 22
          : 18

      const useScoreStyle = hasScore && role !== 'current'
      const roleColor = role ? NODE_ROLE_COLORS[role] : null
      const isHi = Boolean(role) || hiNodes.has(key) || hiNodes.has(String(id))

      const background = useScoreStyle
        ? scoreBg
        : isHi
          ? roleColor?.background || COLORS.nodeHighlight
          : scoreBg || COLORS.node
      const border = useScoreStyle
        ? scoreBorder
        : isHi
          ? roleColor?.border || COLORS.nodeHighlightBorder
          : scoreBorder || COLORS.nodeBorder

      if (logScores && hasScore) {
        // Debug: confirm scaling math runs and values reach DataSet.
        // eslint-disable-next-line no-console
        console.log('[centrality-scale]', {
          nodeId: id,
          nodeIdType: typeof id,
          lookupKey: key,
          rawScore,
          normalized: Number(t.toFixed(4)),
          value,
          size: Number(size.toFixed(1)),
          color: background,
          border,
        })
      }

      const item = {
        id,
        label: n.label != null ? String(n.label) : String(id),
        title: hasScore
          ? `score ${formatScore(rawScore)} · size≈${size.toFixed(0)}`
          : undefined,
        color: {
          background,
          border,
          highlight: {
            background:
              role === 'current'
                ? COLORS.nodeHighlight
                : scoreBg || roleColor?.background || COLORS.nodeHighlight,
            border:
              role === 'current'
                ? COLORS.nodeHighlightBorder
                : scoreBorder || roleColor?.border || COLORS.nodeHighlightBorder,
          },
          hover: {
            background: scoreBg || '#5d82b8',
            border: scoreBorder || '#c5d4e8',
          },
        },
        borderWidth: role === 'current' ? 3.5 : hasScore ? 2.6 : 2,
      }

      if (hasScore) {
        // Primary size driver for vis-network (`setValueRange` uses this).
        item.value = value
        // Also set size so baseSize tracks the intended radius.
        item.size = size
      } else {
        item.size = size
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
        const showWeight = Boolean(isWeighted)
        const role = roles?.[String(id)]
        const isHi = Boolean(role) || hiEdges.has(String(id))
        const roleStyle = role ? EDGE_ROLE_COLORS[role] : null
        return {
          id,
          from: e.from,
          to: e.to,
          label:
            showWeight && e.weight != null ? formatWeight(e.weight) : undefined,
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

    const visNodes = buildVisNodes(payload, { logScores: Boolean(payload.scoreNorm) })
    const visEdges = buildVisEdges(payload)

    nodesDataRef.current.clear()
    edgesDataRef.current.clear()
    if (visNodes.length) nodesDataRef.current.add(visNodes)
    if (visEdges.length) edgesDataRef.current.add(visEdges)

    if (payload.scoreNorm) {
      syncNetworkNodeVisuals(networkRef.current, visNodes)
      logDataSetSample(nodesDataRef.current, 'applyStructure')
      logNetworkSample(networkRef.current, 'applyStructure')
    }

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

  /**
   * Force-apply node visuals. Always clear+add when scores are present so
   * vis-network rebuilds Node options including value/size/color. Then push
   * the same options onto live Network node instances (DataSet alone has been
   * unreliable for centrality styling).
   */
  const applyNodeVisuals = (payload, { forceReplace = false, logScores = false } = {}) => {
    if (!nodesDataRef.current || !edgesDataRef.current || !networkRef.current) return

    // Keep current layout when rebuilding nodes for score styling.
    const positions = {}
    const bodyNodes = networkRef.current.body?.nodes
    if (bodyNodes) {
      for (const node of Object.values(bodyNodes)) {
        if (node?.id == null || typeof node.x !== 'number' || typeof node.y !== 'number') continue
        positions[String(node.id)] = { x: node.x, y: node.y }
      }
    }

    const visNodes = buildVisNodes(payload, { logScores }).map((n) => {
      const pos = positions[String(n.id)]
      if (!pos) return n
      return { ...n, x: pos.x, y: pos.y }
    })
    const visEdges = buildVisEdges(payload)
    const replace = forceReplace || Boolean(payload.scoreNorm)

    if (replace) {
      nodesDataRef.current.clear()
      if (visNodes.length) nodesDataRef.current.add(visNodes)
    } else if (visNodes.length) {
      nodesDataRef.current.update(visNodes)
    }

    if (visEdges.length) edgesDataRef.current.update(visEdges)

    // Belt-and-suspenders: write value/size/color onto live Node options.
    syncNetworkNodeVisuals(networkRef.current, visNodes)

    if (logScores) {
      logDataSetSample(nodesDataRef.current, replace ? 'replace' : 'update')
      logNetworkSample(networkRef.current, replace ? 'replace' : 'update')
    }

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
          // Required for centrality: size is driven by per-node `value`.
          scaling: {
            min: SCORE_SIZE_MIN,
            max: SCORE_SIZE_MAX,
            label: {
              enabled: false,
              drawThreshold: 1000,
            },
          },
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

  // Highlight + centrality score visuals. When scores exist, always rebuild
  // nodes (forceReplace) — DataSet.update alone does not reliably keep value.
  useEffect(() => {
    if (!networkRef.current) return
    const hasScores = Boolean(graphRef.current.scoreNorm)
    // eslint-disable-next-line no-console
    console.log('[centrality-scale] visuals effect', {
      hasScores,
      scoresKeyLen: scoresKey.length,
      nodeCount: graphRef.current.nodes?.length ?? 0,
      sampleRaw: graphRef.current.rawScores
        ? Object.fromEntries(
            Object.entries(graphRef.current.rawScores).slice(0, 5),
          )
        : null,
    })
    applyNodeVisuals(graphRef.current, {
      forceReplace: hasScores,
      logScores: hasScores,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rolesKey, scoresKey])

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

function logDataSetSample(dataSet, label) {
  if (!dataSet) return
  const all = dataSet.get()
  const sample = all
    .filter((n) => n.value != null || n.size != null)
    .slice(0, 6)
    .map((n) => ({
      id: n.id,
      value: n.value,
      size: n.size,
      bg: n.color?.background,
    }))
  // eslint-disable-next-line no-console
  console.log(`[centrality-scale] DataSet after ${label}`, {
    count: all.length,
    sample,
  })
}

function logNetworkSample(network, label) {
  if (!network?.body?.nodes) return
  const sample = Object.values(network.body.nodes)
    .filter((n) => n && n.id != null && !String(n.id).startsWith('edgeId:'))
    .slice(0, 6)
    .map((n) => ({
      id: n.id,
      value: n.options?.value,
      size: n.options?.size,
      bg: n.options?.color?.background,
    }))
  // eslint-disable-next-line no-console
  console.log(`[centrality-scale] Network body after ${label}`, { sample })
}

/** Push computed visuals onto live vis-network Node instances. */
function syncNetworkNodeVisuals(network, visNodes) {
  if (!network?.body?.nodes || !visNodes?.length) return
  const body = network.body.nodes
  for (const item of visNodes) {
    const node =
      body[item.id] ??
      body[String(item.id)] ??
      (Number.isFinite(Number(item.id)) ? body[Number(item.id)] : null)
    if (!node || typeof node.setOptions !== 'function') continue
    const opts = {
      size: item.size,
      color: item.color,
      borderWidth: item.borderWidth,
      title: item.title,
    }
    if (item.value != null && Number.isFinite(Number(item.value))) {
      opts.value = Number(item.value)
    } else {
      opts.value = undefined
    }
    node.setOptions(opts)
  }
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

/**
 * Look up a score for a graph node id, trying string/number key forms.
 * scoreNorm / rawScores are plain objects with canonical string keys.
 */
function lookupScore(scores, id) {
  if (!scores || id == null) return undefined
  if (scores instanceof Map) {
    if (scores.has(id)) return scores.get(id)
    const asString = String(id)
    if (scores.has(asString)) return scores.get(asString)
    if (typeof id === 'string' && /^-?\d+(\.\d+)?$/.test(id)) {
      const asNum = Number(id)
      if (scores.has(asNum)) return scores.get(asNum)
    }
    return undefined
  }
  if (typeof scores !== 'object') return undefined
  if (Object.prototype.hasOwnProperty.call(scores, id)) {
    const v = scores[id]
    return Number.isFinite(Number(v)) ? Number(v) : undefined
  }
  const asString = String(id)
  if (Object.prototype.hasOwnProperty.call(scores, asString)) {
    const v = scores[asString]
    return Number.isFinite(Number(v)) ? Number(v) : undefined
  }
  if (typeof id === 'string' && /^-?\d+$/.test(id)) {
    const asNum = Number(id)
    if (Object.prototype.hasOwnProperty.call(scores, asNum)) {
      const v = scores[asNum]
      return Number.isFinite(Number(v)) ? Number(v) : undefined
    }
  }
  return undefined
}

/**
 * Normalize centrality scores to [0, 1] for size/color mapping.
 * @returns {Record<string, number>|null} plain object with string keys
 */
function normalizeScores(scores) {
  const flat = flattenScoreMap(scores)
  if (!flat) return null
  const entries = Object.entries(flat)
  if (!entries.length) return null
  let min = Infinity
  let max = -Infinity
  for (const [, v] of entries) {
    if (v < min) min = v
    if (v > max) max = v
  }
  const span = max - min
  const out = {}
  for (const [id, v] of entries) {
    // Always string keys — graph node ids may be numbers.
    out[String(id)] = span > 1e-12 ? (v - min) / span : 0.5
  }
  return out
}

/** Flat string-key → number map (handles numeric/string API keys + arrays). */
function flattenScoreMap(scores) {
  if (scores == null) return null
  const out = {}

  const add = (id, value) => {
    if (id == null || id === '') return
    const n = Number(value)
    if (!Number.isFinite(n)) return
    out[String(id)] = n
  }

  if (Array.isArray(scores)) {
    for (const entry of scores) {
      if (Array.isArray(entry) && entry.length >= 2) add(entry[0], entry[1])
      else if (entry && typeof entry === 'object') {
        add(entry.id ?? entry.node ?? entry.vertex, entry.score ?? entry.rank ?? entry.value)
      }
    }
  } else if (typeof scores === 'object') {
    for (const [id, v] of Object.entries(scores)) add(id, v)
  } else {
    return null
  }

  return Object.keys(out).length ? out : null
}

function formatScore(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(4)
}

/** Cool muted blue → saturated gold as score rises. */
function scoreToColor(t) {
  const u = clamp01(t)
  const e = u * u
  const r = Math.round(45 + e * (232 - 45))
  const g = Math.round(70 + e * (186 - 70))
  const b = Math.round(110 + e * (64 - 110))
  return `rgb(${r}, ${g}, ${b})`
}

function scoreToBorder(t) {
  const u = clamp01(t)
  const e = u * u
  const r = Math.round(90 + e * (245 - 90))
  const g = Math.round(120 + e * (220 - 120))
  const b = Math.round(160 + e * (140 - 160))
  return `rgb(${r}, ${g}, ${b})`
}

function clamp01(t) {
  if (!Number.isFinite(t)) return 0
  return Math.min(1, Math.max(0, t))
}
