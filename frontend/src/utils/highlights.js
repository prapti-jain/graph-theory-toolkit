/** Role → color mapping for algorithm animation highlights. */
export const NODE_ROLE_COLORS = {
  visited: {
    background: '#3d5f8a',
    border: '#7ea0c8',
  },
  current: {
    background: '#d4a84b',
    border: '#f0d9a0',
  },
  path: {
    background: '#4faf7a',
    border: '#a6e3c0',
  },
  mst: {
    background: '#5a9e8a',
    border: '#9fd6c4',
  },
  result: {
    background: '#c45c6a',
    border: '#e8a8b2',
  },
  matched: {
    background: '#7a6bb8',
    border: '#c2b8e8',
  },
  rejected: {
    background: '#5a6574',
    border: '#8b97a8',
  },
}

export const EDGE_ROLE_COLORS = {
  visited: { color: '#6f8faf', width: 2.2 },
  current: { color: '#e0b84e', width: 3.2 },
  path: { color: '#5fbf8a', width: 3.0 },
  mst: { color: '#4ec4a0', width: 3.0 },
  result: { color: '#d46a7a', width: 3.0 },
  flow: { color: '#6a9fe0', width: 3.0 },
  rejected: { color: '#5a6574', width: 1.4 },
  consider: { color: '#c4a35a', width: 2.4 },
}

export const ROLE_PRIORITY = {
  current: 100,
  path: 80,
  mst: 75,
  flow: 70,
  result: 70,
  matched: 65,
  consider: 50,
  visited: 30,
  rejected: 10,
}

/**
 * Find graph edge id matching endpoints (undirected-aware).
 * @param {Array<{id?: string|number, from: *, to: *}>} edges
 * @param {*} from
 * @param {*} to
 * @param {boolean} directed
 */
export function findEdgeId(edges, from, to, directed = false) {
  if (from == null || to == null) return null
  const a = String(from)
  const b = String(to)
  for (const e of edges) {
    const ef = String(e.from)
    const et = String(e.to)
    if (ef === a && et === b) return e.id != null ? e.id : `e-${e.from}-${e.to}`
    if (!directed && ef === b && et === a) {
      return e.id != null ? e.id : `e-${e.from}-${e.to}`
    }
  }
  return null
}

/**
 * Accumulate highlight roles from steps[0..endIndex] inclusive.
 * @param {Array<object>} steps
 * @param {number} endIndex
 * @param {Array} graphEdges
 * @param {boolean} directed
 */
export function computeHighlightsFromSteps(
  steps,
  endIndex,
  graphEdges = [],
  directed = false,
) {
  /** @type {Record<string, string>} */
  const nodeRoles = {}
  /** @type {Record<string, string>} */
  const edgeRoles = {}

  const setNode = (id, role) => {
    if (id == null) return
    const key = String(id)
    const prev = nodeRoles[key]
    if (!prev || (ROLE_PRIORITY[role] ?? 0) >= (ROLE_PRIORITY[prev] ?? 0)) {
      nodeRoles[key] = role
    }
  }

  const setEdge = (from, to, role, edgeField) => {
    let edgeId = null
    if (Array.isArray(edgeField) && edgeField.length >= 2) {
      edgeId = findEdgeId(graphEdges, edgeField[0], edgeField[1], directed)
      setNode(edgeField[0], role === 'rejected' ? 'visited' : role)
      setNode(edgeField[1], role === 'rejected' ? 'visited' : role)
    } else if (from != null && to != null) {
      edgeId = findEdgeId(graphEdges, from, to, directed)
    }
    if (edgeId == null) return
    const key = String(edgeId)
    const prev = edgeRoles[key]
    if (!prev || (ROLE_PRIORITY[role] ?? 0) >= (ROLE_PRIORITY[prev] ?? 0)) {
      edgeRoles[key] = role
    }
  }

  // Demote previous "current" to visited as we walk forward by rebuilding.
  const limit = Math.min(endIndex, steps.length - 1)
  for (let i = 0; i <= limit; i += 1) {
    const step = steps[i]
    if (!step || typeof step !== 'object') continue
    const action = step.action

    // Clear transient "current" by treating only the latest step as current
    // — handled after the loop for the last step.

    switch (action) {
      case 'visit':
      case 'discover':
      case 'settle':
      case 'start':
      case 'node_closeness':
      case 'source_done':
        setNode(step.node ?? step.source, 'visited')
        if (step.via != null) setEdge(step.via, step.node, 'visited')
        break
      case 'traverse':
      case 'push':
      case 'relax':
        setNode(step.from ?? step.node, 'visited')
        setNode(step.to, 'visited')
        setEdge(step.from, step.to, 'visited')
        break
      case 'skip':
        if (step.node != null) setNode(step.node, 'visited')
        if (step.from != null && step.to != null) {
          setEdge(step.from, step.to, 'rejected')
        } else if (step.from != null && step.node != null) {
          setEdge(step.from, step.node, 'rejected')
        }
        if (step.edge) setEdge(null, null, 'rejected', step.edge)
        break
      case 'consider':
        setEdge(null, null, 'consider', step.edge)
        break
      case 'accept':
      case 'add':
        setEdge(null, null, 'mst', step.edge)
        if (step.node != null) setNode(step.node, 'mst')
        break
      case 'reject':
        setEdge(null, null, 'rejected', step.edge)
        break
      case 'bridge':
      case 'cut_edge':
        setEdge(null, null, 'result', step.edge)
        break
      case 'articulation_point':
        setNode(step.node, 'result')
        break
      case 'scc':
        ;(step.nodes || []).forEach((n) => setNode(n, 'result'))
        break
      case 'augment':
        ;(step.path || []).forEach(([u, v]) => {
          setNode(u, 'path')
          setNode(v, 'path')
          setEdge(u, v, 'flow')
        })
        break
      case 'match':
        if (step.pair) {
          setNode(step.pair[0], 'matched')
          setNode(step.pair[1], 'matched')
          setEdge(step.pair[0], step.pair[1], 'path')
        }
        break
      case 'reachable_set':
        ;(step.nodes || []).forEach((n) => setNode(n, 'visited'))
        break
      case 'update':
        setNode(step.i, 'visited')
        setNode(step.j, 'visited')
        if (step.via != null) setNode(step.via, 'visited')
        break
      case 'iteration':
      case 'phase':
      case 'potentials':
      case 'potentials_start':
      case 'dijkstra_source':
      case 'build_flow_network':
      case 'update_low':
      case 'back_edge':
      default:
        if (step.node != null) setNode(step.node, 'visited')
        if (step.from != null && step.to != null) {
          setEdge(step.from, step.to, 'visited')
        }
        break
    }
  }

  // Mark the latest step's focus as "current".
  if (limit >= 0) {
    const step = steps[limit]
    const action = step?.action
    if (
      action === 'visit' ||
      action === 'discover' ||
      action === 'settle' ||
      action === 'start'
    ) {
      setNode(step.node, 'current')
    } else if (
      action === 'traverse' ||
      action === 'relax' ||
      action === 'push'
    ) {
      setNode(step.to ?? step.node, 'current')
      setEdge(step.from, step.to, 'current')
    } else if (action === 'consider' || action === 'accept' || action === 'add') {
      if (step.edge) {
        setEdge(null, null, 'current', step.edge)
        setNode(step.edge[0], 'current')
      }
      if (step.node != null) setNode(step.node, 'current')
    } else if (action === 'augment' && step.path?.length) {
      const last = step.path[step.path.length - 1]
      setNode(last[1] ?? last[0], 'current')
    }
  }

  return {
    nodeHighlightRoles: nodeRoles,
    edgeHighlightRoles: edgeRoles,
    highlightedNodes: new Set(Object.keys(nodeRoles)),
    highlightedEdges: new Set(Object.keys(edgeRoles)),
  }
}
