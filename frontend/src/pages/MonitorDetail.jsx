import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api.js'
import { INTERVAL_OPTIONS, formatDate, formatInterval, timeAgo } from '../lib/format.js'
import DiffView, { SnapshotText, computeDiff } from '../components/DiffView.jsx'

export default function MonitorDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [monitor, setMonitor] = useState(null)
  const [snapshots, setSnapshots] = useState([]) // newest first, as returned by the API
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState({})

  const load = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([api.getMonitor(id), api.getChanges(id)])
      setMonitor(m)
      setSnapshots(s)
      setError('')
    } catch (err) {
      setError(err.status === 404 ? 'This URL was not found.' : err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  // Each snapshot is compared with the one that came right before it (the next one in the list).
  const entries = useMemo(
    () =>
      snapshots.map((snap, i) => {
        const previous = snapshots[i + 1]
        return {
          snap,
          previous,
          diff: previous ? computeDiff(previous.content, snap.content) : null,
        }
      }),
    [snapshots],
  )

  async function handleIntervalChange(e) {
    const value = Number(e.target.value)
    setSaving(true)
    try {
      setMonitor(await api.updateMonitor(id, { check_interval: value }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm('Stop tracking this URL and delete its history?')) return
    try {
      await api.deleteMonitor(id)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <div className="empty">Loading…</div>

  if (!monitor) {
    return (
      <>
        <Link to="/" className="back">← All URLs</Link>
        <div className="alert alert-error">{error || 'Something went wrong.'}</div>
      </>
    )
  }

  const changeCount = Math.max(snapshots.length - 1, 0)
  const intervalOptions = INTERVAL_OPTIONS.some((o) => o.value === monitor.check_interval)
    ? INTERVAL_OPTIONS
    : [
        { value: monitor.check_interval, label: `Every ${formatInterval(monitor.check_interval)}` },
        ...INTERVAL_OPTIONS,
      ]

  return (
    <>
      <Link to="/" className="back">← All URLs</Link>

      <header className="detail-head">
        <div>
          <h1 className="detail-title">{monitor.url}</h1>
          <a className="muted" href={monitor.url} target="_blank" rel="noreferrer noopener">
            Open page ↗
          </a>
        </div>
        <button className="btn btn-danger" onClick={handleDelete}>
          Delete
        </button>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stats">
        <div className="stat">
          <span className="stat-label">Status</span>
          <span className={`pill ${monitor.status ? 'pill-on' : 'pill-off'}`}>
            {monitor.status ? 'Active' : 'Paused'}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Last checked</span>
          <span className="stat-value" title={formatDate(monitor.last_check)}>
            {timeAgo(monitor.last_check)}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Changes found</span>
          <span className="stat-value">{changeCount}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Check frequency</span>
          <select value={monitor.check_interval} onChange={handleIntervalChange} disabled={saving}>
            {intervalOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="section-head">
        <h2>Change history</h2>
        <button className="btn btn-ghost" onClick={load}>
          Refresh
        </button>
      </div>

      {changeCount === 0 && (
        <div className="empty">
          <strong>No changes yet.</strong>
          <span className="muted">
            Trackly saved the first version of this page. New versions appear here when the page
            changes.
          </span>
        </div>
      )}

      <ol className="timeline">
        {entries.map(({ snap, diff }, i) => {
          const isFirst = !diff
          const isOpen = expanded[snap.id] ?? i === 0
          return (
            <li key={snap.id} className="timeline-item">
              <span className={`dot ${isFirst ? 'dot-first' : ''}`} aria-hidden="true" />
              <div className="card">
                <button
                  className="card-head"
                  onClick={() => setExpanded((prev) => ({ ...prev, [snap.id]: !isOpen }))}
                  aria-expanded={isOpen}
                >
                  <div>
                    <strong>{isFirst ? 'First snapshot' : 'Page changed'}</strong>
                    <span className="muted"> · {formatDate(snap.created_at)}</span>
                  </div>
                  <div className="card-badges">
                    {diff && (
                      <>
                        <span className="badge badge-add">+{diff.added}</span>
                        <span className="badge badge-del">−{diff.removed}</span>
                      </>
                    )}
                    <span className="chevron">{isOpen ? '▾' : '▸'}</span>
                  </div>
                </button>
                {isOpen && (
                  <div className="card-body">
                    {isFirst ? <SnapshotText content={snap.content} /> : <DiffView rows={diff.rows} />}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </>
  )
}
