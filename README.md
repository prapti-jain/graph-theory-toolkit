# Graph Theory Toolkit

A from-scratch implementation and interactive visualizer for classical graph algorithms across five areas — traversal and connectivity, shortest paths, MST, flows and matching, and centrality. Implementations are validated against NetworkX (45 passing pytest cases) and paired with an empirical complexity-benchmarking harness.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://graph-theory-toolkit.vercel.app)
[![API](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge&logo=render)](https://graph-theory-toolkit.onrender.com)

- **Live demo:** https://graph-theory-toolkit.vercel.app
- **Backend API:** https://graph-theory-toolkit.onrender.com  
  Health check: [`GET /health`](https://graph-theory-toolkit.onrender.com/health)

## Algorithms Implemented

**Traversal / connectivity**
- BFS, DFS, Topological Sort, Tarjan's SCC, Bridges, Articulation Points

**Shortest paths**
- Dijkstra, Bellman–Ford, Floyd–Warshall, A*, Johnson's

**Minimum spanning trees**
- Kruskal's, Prim's

**Flows / matching**
- Edmonds–Karp Max-Flow, Min-Cut, Bipartite Matching, Hopcroft–Karp

**Centrality**
- PageRank, Betweenness, Closeness, Eigenvector

## Tech Stack

| Layer | Stack |
|-------|--------|
| **Backend** | FastAPI, NetworkX (validation / dataset source only), pytest |
| **Frontend** | React, Vite, vis-network, Recharts |
| **Deployment** | Render (API), Vercel (UI) |

## Local Development

### Project structure

```
graph-theory-toolkit/
├── backend/          # FastAPI API + graph core + algorithms
├── frontend/         # Vite + React visualization UI
├── docs/             # Documentation
└── README.md
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API: `http://localhost:8000` · Health: `GET /health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173` (expects the backend on port 8000 by default).

Optional: copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL` if the API is not on localhost.

## Documentation

The `docs/` directory is reserved for write-ups (`00-overview.md` … `07-references.md`). Those pages are not written yet; only a placeholder is present. See [`docs/`](docs/) for current contents.
