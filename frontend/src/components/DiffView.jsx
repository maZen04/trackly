import { useMemo, useState } from 'react'
import { diffLines } from 'diff'

// Splits a diff chunk into lines without the trailing empty entry.
function toLines(value) {
  const lines = value.split('\n')
  if (lines[lines.length - 1] === '') lines.pop()
  return lines
}

// Shows what was added / removed between two versions of a page's text.
// Unchanged runs longer than 2*CONTEXT lines are collapsed.
const CONTEXT = 2

export function computeDiff(oldText, newText) {
  const parts = diffLines(oldText, newText)
  let added = 0
  let removed = 0
  const rows = []

  parts.forEach((part) => {
    const lines = toLines(part.value)
    if (part.added) {
      added += lines.length
      lines.forEach((text) => rows.push({ type: 'add', text }))
    } else if (part.removed) {
      removed += lines.length
      lines.forEach((text) => rows.push({ type: 'del', text }))
    } else if (lines.length > CONTEXT * 2 + 1) {
      lines.slice(0, CONTEXT).forEach((text) => rows.push({ type: 'same', text }))
      rows.push({ type: 'gap', text: `${lines.length - CONTEXT * 2} unchanged lines` })
      lines.slice(-CONTEXT).forEach((text) => rows.push({ type: 'same', text }))
    } else {
      lines.forEach((text) => rows.push({ type: 'same', text }))
    }
  })

  return { rows, added, removed }
}

const MARK = { add: '+', del: '−', same: ' ', gap: '⋯' }

export default function DiffView({ rows }) {
  return (
    <div className="diff" role="table">
      {rows.map((row, i) => (
        <div key={i} className={`diff-row diff-${row.type}`} role="row">
          <span className="diff-mark" aria-hidden="true">
            {MARK[row.type]}
          </span>
          <span className="diff-text">{row.text}</span>
        </div>
      ))}
    </div>
  )
}

// Plain page text for the very first snapshot (nothing to compare with).
export function SnapshotText({ content }) {
  const [open, setOpen] = useState(false)
  const preview = useMemo(() => content.split('\n').slice(0, 12).join('\n'), [content])
  const hasMore = content.split('\n').length > 12

  return (
    <div>
      <pre className="snapshot-text">{open ? content : preview}</pre>
      {hasMore && (
        <button className="btn btn-link" onClick={() => setOpen((v) => !v)}>
          {open ? 'Show less' : 'Show full text'}
        </button>
      )}
    </div>
  )
}
