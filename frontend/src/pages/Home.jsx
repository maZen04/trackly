import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { INTERVAL_OPTIONS, formatInterval, hostOf, timeAgo } from '../lib/format.js'

export default function Home() {
  const [monitors, setMonitors] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [url, setUrl] = useState('')
  const [interval, setIntervalValue] = useState(60)
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  const load = useCallback(async () => {
    try {
      setMonitors(await api.listMonitors())
      setLoadError('')
    } catch (err) {
      setLoadError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleAdd(e) {
    e.preventDefault()
    setAddError('')
    let value = url.trim()
    if (!value) return
    if (!/^https?:\/\//i.test(value)) value = `https://${value}`

    setAdding(true)
    try {
      const created = await api.createMonitor(value, Number(interval))
      setMonitors((prev) => [created, ...prev])
      setUrl('')
    } catch (err) {
      setAddError(err.message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Watch any page for changes</h1>
        <p className="muted">
          Paste a URL and Trackly will check it on a schedule and keep every version it finds.
        </p>

        <form className="add-form" onSubmit={handleAdd}>
          <input
            className="add-input"
            type="text"
            inputMode="url"
            placeholder="https://example.com/pricing"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="URL to track"
            required
          />
          <select
            className="add-select"
            value={interval}
            onChange={(e) => setIntervalValue(e.target.value)}
            aria-label="Check frequency"
          >
            {INTERVAL_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" disabled={adding}>
            {adding ? 'Checking page…' : 'Track URL'}
          </button>
        </form>
        {addError && <div className="alert alert-error">{addError}</div>}
      </section>

      <section>
        <div className="section-head">
          <h2>Your URLs</h2>
          {!loading && <span className="muted">{monitors.length} tracked</span>}
        </div>

        {loading && <div className="empty">Loading…</div>}
        {loadError && <div className="alert alert-error">{loadError}</div>}

        {!loading && !loadError && monitors.length === 0 && (
          <div className="empty">
            <strong>Nothing tracked yet.</strong>
            <span className="muted">Add your first URL above to get started.</span>
          </div>
        )}

        <ul className="monitor-list">
          {monitors.map((m) => (
            <li key={m.id}>
              <Link to={`/monitors/${m.id}`} className="monitor-card">
                <div className="monitor-main">
                  <span className="monitor-host">{hostOf(m.url)}</span>
                  <span className="monitor-url">{m.url}</span>
                </div>
                <div className="monitor-meta">
                  <span className={`pill ${m.status ? 'pill-on' : 'pill-off'}`}>
                    {m.status ? 'Active' : 'Paused'}
                  </span>
                  <span className="muted">Every {formatInterval(m.check_interval)}</span>
                  <span className="muted">Checked {timeAgo(m.last_check)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
