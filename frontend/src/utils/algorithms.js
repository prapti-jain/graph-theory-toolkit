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
        needs: ['start'],
        run: api.runPrims,
        preferUndirected: true,
        startOptional: true,
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
  if (params.leftNodes) {
    body.left_nodes = parseIdList(params.leftNodes)
  }
  if (params.rightNodes) {
    body.right_nodes = parseIdList(params.rightNodes)
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
    case 'prims':
      return {
        title: 'Minimum spanning tree',
        lines: [
          `Total weight: ${formatNum(result.total_weight)}`,
          `Edges: ${(result.edges || [])
            .map((e) => `${e.u}–${e.v} (${formatNum(e.weight)})`)
            .join(', ')}`,
        ],
      }
    case 'mst-compare':
      return {
        title: 'MST comparison',
        lines: [
          `Shared total weight: ${formatNum(result.total_weight)}`,
          result.note || `Faster: ${result.faster}`,
        ],
      }
    case 'max-flow':
      return {
        title: 'Maximum flow',
        lines: [`Max flow value: ${formatNum(result.max_flow)}`],
      }
    case 'min-cut':
      return {
        title: 'Minimum cut',
        lines: [
          `Cut value: ${formatNum(result.cut_value)}`,
          `Cut edges: ${(result.cut_edges || [])
            .map((e) => `${e.u}→${e.v}`)
            .join(', ') || 'none'}`,
        ],
      }
    case 'bipartite-matching':
    case 'hopcroft-karp':
      return {
        title: 'Maximum matching',
        lines: [
          `Size: ${result.size}`,
          `Pairs: ${(result.matching || [])
            .map((p) => `${p.left}–${p.right}`)
            .join(', ') || 'none'}`,
        ],
      }
    case 'pagerank':
      return {
        title: 'PageRank',
        lines: [
          `Converged in ${result.iterations} iterations`,
          topScores(result.ranks, 5, 'rank'),
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
            ? `Iterations: ${result.iterations}`
            : null,
          topScores(result.scores || result.ranks, 5, 'score'),
        ].filter(Boolean),
      }
    default:
      return { title: 'Result', lines: [JSON.stringify(result).slice(0, 200)] }
  }
}

function topScores(map, k, label) {
  if (!map) return `No ${label}s`
  const ranked = Object.entries(map)
    .map(([id, v]) => [id, Number(v)])
    .sort((a, b) => b[1] - a[1])
    .slice(0, k)
  return `Top ${label}s: ${ranked
    .map(([id, v]) => `${id}=${formatNum(v)}`)
    .join(', ')}`
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
