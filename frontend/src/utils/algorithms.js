import * as api from '../api/client'

/**
 * Algorithm catalog for the visualizer UI.
 * @typedef {'start'|'goal'|'source'|'sink'|'leftRight'|'coords'} AlgoNeed
 */

/** @type {Array<{id: string, label: string, algorithms: Array<object>}>} */
export const ALGORITHM_CATEGORIES = [
  {
    id: 'traversal',
    label: 'Traversal',
    algorithms: [
      { id: 'bfs', label: 'BFS', needs: ['start'], run: api.runBfs },
      { id: 'dfs', label: 'DFS', needs: ['start'], run: api.runDfs },
      { id: 'scc', label: 'SCC (Tarjan)', needs: [], run: api.runScc, preferDirected: true },
      { id: 'bridges', label: 'Bridges', needs: [], run: api.runBridges, preferUndirected: true },
      {
        id: 'articulation',
        label: 'Articulation Points',
        needs: [],
        run: api.runArticulationPoints,
        preferUndirected: true,
      },
    ],
  },
  {
    id: 'shortest',
    label: 'Shortest Paths',
    algorithms: [
      {
        id: 'dijkstra',
        label: 'Dijkstra',
        needs: ['start', 'goal'],
        goalOptional: true,
        run: api.runDijkstra,
      },
      {
        id: 'bellman-ford',
        label: 'Bellman–Ford',
        needs: ['start', 'goal'],
        goalOptional: true,
        run: api.runBellmanFord,
      },
      {
        id: 'floyd-warshall',
        label: 'Floyd–Warshall',
        needs: [],
        run: api.runFloydWarshall,
      },
      {
        id: 'a-star',
        label: 'A*',
        needs: ['start', 'goal', 'coords'],
        run: api.runAStar,
      },
      { id: 'johnsons', label: "Johnson's", needs: [], run: api.runJohnsons },
    ],
  },
  {
    id: 'mst',
    label: 'MST',
    algorithms: [
      {
        id: 'kruskals',
        label: "Kruskal's",
        needs: [],
        run: api.runKruskals,
        preferUndirected: true,
      },
      {
        id: 'prims',
        label: "Prim's",
        // Grows from an arbitrary node on the backend; no start/goal UI.
        needs: [],
        run: api.runPrims,
        preferUndirected: true,
      },
      {
        id: 'mst-compare',
        label: 'Compare Kruskal / Prim',
        needs: [],
        run: api.runMstCompare,
        preferUndirected: true,
      },
    ],
  },
  {
    id: 'flows',
    label: 'Flows',
    algorithms: [
      {
        id: 'max-flow',
        label: 'Max-Flow (Edmonds–Karp)',
        needs: ['source', 'sink'],
        run: api.runMaxFlow,
        preferDirected: true,
      },
      {
        id: 'min-cut',
        label: 'Min-Cut',
        needs: ['source', 'sink'],
        run: api.runMinCut,
        preferDirected: true,
      },
      {
        id: 'bipartite-matching',
        label: 'Bipartite Matching',
        needs: ['leftRight'],
        run: api.runBipartiteMatching,
      },
      {
        id: 'hopcroft-karp',
        label: 'Hopcroft–Karp',
        needs: ['leftRight'],
        run: api.runHopcroftKarp,
      },
    ],
  },
  {
    id: 'centrality',
    label: 'Centrality',
    algorithms: [
      { id: 'pagerank', label: 'PageRank', needs: [], run: api.runPagerank },
      {
        id: 'betweenness',
        label: 'Betweenness',
        needs: [],
        run: api.runBetweenness,
      },
      { id: 'closeness', label: 'Closeness', needs: [], run: api.runCloseness },
      {
        id: 'eigenvector',
        label: 'Eigenvector',
        needs: [],
        run: api.runEigenvector,
      },
    ],
  },
]

export function findAlgorithm(algorithmId) {
  for (const cat of ALGORITHM_CATEGORIES) {
    const found = cat.algorithms.find((a) => a.id === algorithmId)
    if (found) return { ...found, category: cat.id, categoryLabel: cat.label }
  }
  return null
}

/**
 * Build request body from graph + algorithm params.
 */
export function buildAlgorithmBody(graph, algorithmId, params) {
  const algo = findAlgorithm(algorithmId)
  if (!algo) throw new Error(`Unknown algorithm: ${algorithmId}`)

  const body = {
    edges: (graph.edges || []).map((e) =>
      graph.weighted || e.weight != null
        ? [e.from, e.to, e.weight ?? 1]
        : [e.from, e.to],
    ),
    nodes: (graph.nodes || []).map((n) => n.id),
    directed: Boolean(graph.directed),
    weighted: Boolean(graph.weighted),
  }

  if (params.start !== '' && params.start != null && params.start !== undefined) {
    body.start = coerceId(params.start)
  }
  if (params.goal !== '' && params.goal != null) {
    body.goal = coerceId(params.goal)
  }
  if (params.source !== '' && params.source != null) {
    body.source = coerceId(params.source)
  }
  if (params.sink !== '' && params.sink != null) {
    body.sink = coerceId(params.sink)
  }
  if (params.leftNodes != null && params.leftNodes !== '') {
    body.left_nodes = Array.isArray(params.leftNodes)
      ? params.leftNodes.map(coerceId)
      : parseIdList(params.leftNodes)
  }
  if (params.rightNodes != null && params.rightNodes !== '') {
    body.right_nodes = Array.isArray(params.rightNodes)
      ? params.rightNodes.map(coerceId)
      : parseIdList(params.rightNodes)
  }

  // A* coordinates: place nodes on a circle if none exist.
  if (algo.needs.includes('coords')) {
    const coords = {}
    const list = graph.nodes || []
    const n = list.length || 1
    list.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / n
      coords[String(node.id)] = [
        Math.cos(angle) * 100,
        Math.sin(angle) * 100,
      ]
    })
    body.coordinates = coords
  }

  return body
}

/**
 * Human-readable final result summary from API response.
 */
export function formatAlgorithmResult(algorithmId, result) {
  if (!result) return null

  switch (algorithmId) {
    case 'bfs': {
      const order = result.order || []
      return {
        title: 'BFS complete',
        lines: [
          `Visit order: ${order.join(' → ') || '—'}`,
          `Reachable nodes: ${order.length}`,
        ],
      }
    }
    case 'dfs':
      return {
        title: 'DFS complete',
        lines: [`Visit order: ${(result.order || []).join(' → ') || '—'}`],
      }
    case 'scc':
      return {
        title: 'Strongly connected components',
        lines: [
          `Components: ${(result.components || []).length}`,
          ...(result.components || [])
            .slice(0, 6)
            .map((c, i) => `  C${i + 1}: {${c.join(', ')}}`),
        ],
      }
    case 'bridges':
      return {
        title: 'Bridges',
        lines: [
          `Count: ${(result.bridges || []).length}`,
          `Edges: ${(result.bridges || [])
            .map((e) => `${e[0]}–${e[1]}`)
            .join(', ') || 'none'}`,
        ],
      }
    case 'articulation':
      return {
        title: 'Articulation points',
        lines: [
          `Nodes: ${(result.articulation_points || []).join(', ') || 'none'}`,
        ],
      }
    case 'dijkstra':
    case 'bellman-ford':
    case 'a-star': {
      const path = result.path
      const distances = result.distances || {}
      const dist =
        result.distance ??
        (path && path.length
          ? distances[String(path[path.length - 1])]
          : null)

      if (path && path.length) {
        return {
          title: algorithmId === 'a-star' ? 'A* shortest path' : 'Shortest path',
          lines: [
            `Path: ${path.join(' → ')}`,
            `Total distance: ${formatNum(dist)}`,
          ],
        }
      }

      // No goal (or unreachable): show full distance table from start.
      const rows = Object.entries(distances)
        .map(([node, d]) => [node, Number(d)])
        .sort((a, b) => {
          const na = Number(a[0])
          const nb = Number(b[0])
          if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb
          return String(a[0]).localeCompare(String(b[0]))
        })

      return {
        title: 'Shortest distances from start',
        lines:
          rows.length === 0
            ? ['No reachable nodes.']
            : [
                'No goal selected — distances to every reachable node:',
                ...rows.map(([node, d]) => `${node}: ${formatNum(d)}`),
              ],
      }
    }
    case 'floyd-warshall':
    case 'johnsons':
      return {
        title: algorithmId === 'johnsons' ? "Johnson's APSP" : 'Floyd–Warshall APSP',
        lines: [
          result.path_distance != null
            ? `Selected pair distance: ${formatNum(result.path_distance)}`
            : 'All-pairs distance matrix computed',
        ],
      }
    case 'kruskals':
    case 'prims': {
      const edges = result.edges || []
      return {
        title: 'Minimum spanning tree',
        lines: [
          `Total weight: ${formatNum(result.total_weight)}`,
          `MST edges (${edges.length}):`,
          ...edges.map(
            (e) => `${e.u} – ${e.v}  (weight ${formatNum(e.weight)})`,
          ),
        ],
      }
    }
    case 'mst-compare': {
      const fmtEdges = (edges) =>
        (edges || [])
          .map((e) => `${e.u}–${e.v} (${formatNum(e.weight)})`)
          .join(', ') || '—'
      const k = result.kruskals || {}
      const p = result.prims || {}
      return {
        title: 'MST comparison',
        lines: [
          `Shared total weight: ${formatNum(result.total_weight)}`,
          `Kruskal's: ${formatNum(k.time_ms)} ms · ${fmtEdges(k.edges)}`,
          `Prim's: ${formatNum(p.time_ms)} ms · ${fmtEdges(p.edges)}`,
          result.note || `Faster: ${result.faster}`,
        ],
      }
    }
    case 'max-flow':
      return {
        title: 'Maximum flow',
        lines: [
          `Max flow value: ${formatNum(result.max_flow)}`,
          ...(result.flow || []).length
            ? [
                `Flow on edges (${result.flow.length}):`,
                ...result.flow.map(
                  (e) => `${e.u} → ${e.v}  (flow ${formatNum(e.flow)})`,
                ),
              ]
            : [],
        ],
      }
    case 'min-cut': {
      const cutEdges = result.cut_edges || []
      return {
        title: 'Minimum cut',
        lines: [
          `Cut value: ${formatNum(result.cut_value)}`,
          `Source side: {${(result.source_side || []).join(', ') || '—'}}`,
          `Sink side: {${(result.sink_side || []).join(', ') || '—'}}`,
          `Cut edges (${cutEdges.length}):`,
          ...cutEdges.map(
            (e) =>
              `${e.u} → ${e.v}` +
              (e.capacity != null ? `  (cap ${formatNum(e.capacity)})` : ''),
          ),
        ],
      }
    }
    case 'bipartite-matching':
    case 'hopcroft-karp': {
      const pairs = result.matching || []
      return {
        title: 'Maximum matching',
        lines: [
          `Matching size: ${result.size}`,
          `Matched pairs (${pairs.length}):`,
          ...pairs.map((p) => `${p.left} – ${p.right}`),
        ],
      }
    }
    case 'pagerank':
      return {
        title: 'PageRank',
        lines: [
          `Converged in ${result.iterations} iterations`,
          'Ranks (highest → lowest):',
          ...sortedScoreLines(result.ranks),
        ],
      }
    case 'betweenness':
    case 'closeness':
    case 'eigenvector':
      return {
        title:
          algorithmId === 'betweenness'
            ? 'Betweenness centrality'
            : algorithmId === 'closeness'
              ? 'Closeness centrality'
              : 'Eigenvector centrality',
        lines: [
          result.iterations != null
            ? `Converged in ${result.iterations} iterations`
            : null,
          'Scores (highest → lowest):',
          ...sortedScoreLines(result.scores || result.ranks),
        ].filter(Boolean),
      }
    default:
      return { title: 'Result', lines: [JSON.stringify(result).slice(0, 200)] }
  }
}

/**
 * Score map for canvas scaling, or null if not a centrality result.
 *
 * Always returns a fresh plain object with **string** keys and numeric values.
 * API JSON keys are strings ("33") while graph.nodes[].id is often a number (33);
 * canonicalizing here prevents silent Map/object lookup misses in GraphCanvas.
 */
export function getCentralityScores(algorithmId, result) {
  if (!result || !algorithmId) return null
  let raw = null
  if (algorithmId === 'pagerank') raw = result.ranks
  else if (
    algorithmId === 'betweenness' ||
    algorithmId === 'closeness' ||
    algorithmId === 'eigenvector'
  ) {
    raw = result.scores
  }
  return canonicalizeScoreMap(raw)
}

/**
 * Coerce API ranks/scores into `{ [stringId]: number }` or null.
 * Accepts plain objects or arrays of `[id, score]` / `{id|node, score|rank|value}`.
 */
export function canonicalizeScoreMap(raw) {
  if (raw == null) return null
  const out = {}

  const add = (id, value) => {
    if (id == null || id === '') return
    const n = Number(value)
    if (!Number.isFinite(n)) return
    out[String(id)] = n
  }

  if (Array.isArray(raw)) {
    for (const entry of raw) {
      if (Array.isArray(entry) && entry.length >= 2) {
        add(entry[0], entry[1])
      } else if (entry && typeof entry === 'object') {
        add(entry.id ?? entry.node ?? entry.vertex, entry.score ?? entry.rank ?? entry.value)
      }
    }
  } else if (typeof raw === 'object') {
    for (const [id, value] of Object.entries(raw)) {
      add(id, value)
    }
  } else {
    return null
  }

  return Object.keys(out).length ? out : null
}

export function isCentralityAlgorithm(algorithmId) {
  return (
    algorithmId === 'pagerank' ||
    algorithmId === 'betweenness' ||
    algorithmId === 'closeness' ||
    algorithmId === 'eigenvector'
  )
}

function sortedScoreLines(map) {
  if (!map || typeof map !== 'object') return ['No scores']
  const ranked = Object.entries(map)
    .map(([id, v]) => [id, Number(v)])
    .filter(([, v]) => Number.isFinite(v))
    .sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1]
      return String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true })
    })
  if (!ranked.length) return ['No scores']
  return ranked.map(
    ([id, v], i) => `${i + 1}. node ${id}: ${formatNum(v)}`,
  )
}

function formatNum(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/\.?0+$/, '')
}

function coerceId(raw) {
  const s = String(raw).trim()
  if (/^-?\d+$/.test(s)) return Number(s)
  return s
}

function parseIdList(raw) {
  return String(raw)
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map(coerceId)
}

/**
 * Whether the graph is *actually* weighted for UI purposes.
 *
 * Trusts ``graph.weighted`` when false. When true (or missing), inspects
 * edge weights: if every edge is unit weight ``1``, treat as unweighted
 * (covers grid / karate / stale flags left on after an unweighted load).
 */
export function isGraphWeighted(graph) {
  if (!graph) return false
  if (graph.weighted === false) return false

  const edges = graph.edges || []
  if (edges.length === 0) return Boolean(graph.weighted)

  return edges.some((e) => {
    if (e.weight == null || e.weight === '') return false
    const w = Number(e.weight)
    return Number.isFinite(w) && w !== 1
  })
}
