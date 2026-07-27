import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [status, setStatus] = useState('checking…')
  const [error, setError] = useState(null)

  useEffect(() => {
    axios
      .get(`${API_BASE}/health`)
      .then((res) => {
        setStatus(res.data?.status ?? JSON.stringify(res.data))
        setError(null)
      })
      .catch((err) => {
        setStatus('unavailable')
        setError(err.message)
      })
  }, [])

  return (
    <main className="app">
      <h1>Graph Theory Toolkit</h1>
      <p>
        Backend health: <strong>{status}</strong>
      </p>
      {error && <p className="error">{error}</p>}
    </main>
  )
}

export default App
