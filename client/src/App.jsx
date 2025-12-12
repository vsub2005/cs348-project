import { useEffect, useMemo, useState } from 'react'

const api = async (path, options = {}) => {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    // Try to extract useful error text
    let msg = await res.text()
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

export default function App() {
  // Reference data (dynamic dropdowns)
  const [sports, setSports] = useState([])
  const [teams, setTeams] = useState([])        // all teams
  const [venues, setVenues] = useState([])

  // Games list
  const [games, setGames] = useState([])

  // CRUD form
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    sport_id: '', home_team_id: '', away_team_id: '', venue_id: '',
    date: '', time: '', home_score: '', away_score: '', status: 'scheduled',
    row_version: 0, // carry for optimistic concurrency
  })

  // REPORT state
  const today = new Date().toISOString().slice(0,10)
  const [reportFilters, setReportFilters] = useState({
    from: today, to: today, sport_id: '', team_id: '',
  })
  const [report, setReport] = useState(null) // {filters, stats, rows}

  const blockNonIntegerKeys = (e) => {
    const bad = ['e','E','+','-','.']
    if (bad.includes(e.key)) e.preventDefault()
  }
  const preventNonDigitPaste = (e) => {
    const txt = (e.clipboardData || window.clipboardData).getData('text')
    if (!/^\d*$/.test(txt)) e.preventDefault()
  }

  useEffect(() => {
    (async () => {
      const [s, v, t, g] = await Promise.all([
        api('/api/sports'), api('/api/venues'), api('/api/teams'), api('/api/games')
      ])
      setSports(s); setVenues(v); setTeams(t); setGames(g)
    })().catch(err => alert(err.message))
  }, [])

  // Teams filtered by selected sport
  const teamsForSport = useMemo(() => {
    if (!form.sport_id) return []
    return teams.filter(t => String(t.sport_id) === String(form.sport_id))
  }, [teams, form.sport_id])

  // Teams filtered by report sport
  const reportTeams = useMemo(() => {
    if (!reportFilters.sport_id) return []
    return teams.filter(t => String(t.sport_id) === String(reportFilters.sport_id))
  }, [teams, reportFilters.sport_id])

  const resetForm = () => {
    setEditingId(null)
    setForm({
      sport_id: '', home_team_id: '', away_team_id: '', venue_id: '',
      date: '', time: '', home_score: '', away_score: '', status: 'scheduled',
      row_version: 0,
    })
  }

  const reloadGames = async () => setGames(await api('/api/games'))

  const onSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      sport_id: numOrNull(form.sport_id),
      home_team_id: numOrNull(form.home_team_id),
      away_team_id: numOrNull(form.away_team_id),
      venue_id: numOrNull(form.venue_id),
      date: form.date || null,
      time: form.time || null,
      status: form.status || 'scheduled',
      home_score: numOrNull(form.home_score),
      away_score: numOrNull(form.away_score),
      row_version: form.row_version ?? 0,
    }
    try {
      if (editingId) {
        const updated = await api(`/api/games/${editingId}`, { method: 'PUT', body: JSON.stringify(payload) })
        await reloadGames()
        // Load server's new row_version to the form (if you keep editing)
        setEditingId(updated.id)
        setForm({
          sport_id: String(updated.sport_id),
          home_team_id: String(updated.home_team_id),
          away_team_id: String(updated.away_team_id),
          venue_id: updated.venue_id ? String(updated.venue_id) : '',
          date: updated.date, time: updated.time,
          home_score: updated.home_score ?? '',
          away_score: updated.away_score ?? '',
          status: updated.status || 'scheduled',
          row_version: updated.row_version ?? 0,
        })
      } else {
        await api('/api/games', { method: 'POST', body: JSON.stringify(payload) })
        await reloadGames()
        resetForm()
      }
    } catch (err) {
      // Look for 409 payload
      if (err.message.includes('"error": "conflict"') || err.message.includes('409')) {
        alert("Update conflict: someone else changed this game. Reload the list and try again.")
      } else {
        alert(err.message)
      }
    }
  }

  const onEdit = (g) => {
    setEditingId(g.id)
    setForm({
      sport_id: String(g.sport_id),
      home_team_id: String(g.home_team_id),
      away_team_id: String(g.away_team_id),
      venue_id: g.venue_id ? String(g.venue_id) : '',
      date: g.date, time: g.time,
      home_score: g.home_score ?? '', away_score: g.away_score ?? '',
      status: g.status || 'scheduled',
      row_version: g.row_version ?? 0,
    })
  }

  const onDelete = async (id) => {
    if (!confirm('Delete this game?')) return
    try {
      // send row_version if we're deleting the row being edited
      const opt = (editingId === id)
        ? { method: 'DELETE', body: JSON.stringify({ row_version: form.row_version ?? 0 }) }
        : { method: 'DELETE' }
      await api(`/api/games/${id}`, opt)
      await reloadGames()
      if (editingId === id) resetForm()
    } catch (err) {
      if (err.message.includes('"error": "conflict"') || err.message.includes('409')) {
        alert("Delete conflict: someone else changed this game. Reload the list and try again.")
      } else {
        alert(err.message)
      }
    }
  }

  // Running report
  const runReport = async () => {
    const qs = new URLSearchParams()
    if (reportFilters.from) qs.set('from', reportFilters.from)
    if (reportFilters.to) qs.set('to', reportFilters.to)
    if (reportFilters.sport_id) qs.set('sport_id', reportFilters.sport_id)
    if (reportFilters.team_id) qs.set('team_id', reportFilters.team_id)
    const data = await api(`/api/report/games?${qs.toString()}`)
    setReport(data)
  }

  const clearReport = () => setReport(null)

  return (
    <div style={page}>
      <h1 style={{ marginTop: 0 }}>Intramural League — Games</h1>

      {/* CRUD */}
      <form onSubmit={onSubmit} style={formGrid}>
        <label style={labelCol}>
          <span>Sport</span>
          <select
            value={form.sport_id}
            onChange={(e) => setForm({ ...form, sport_id: e.target.value, home_team_id: '', away_team_id: '' })}
            required
          >
            <option value="">– select –</option>
            {sports.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>

        <label style={labelCol}>
          <span>Home Team</span>
          <select value={form.home_team_id} onChange={(e)=>setForm({...form, home_team_id:e.target.value})} required disabled={!form.sport_id}>
            <option value="">– select –</option>
            {teamsForSport.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>

        <label style={labelCol}>
          <span>Away Team</span>
          <select value={form.away_team_id} onChange={(e)=>setForm({...form, away_team_id:e.target.value})} required disabled={!form.sport_id}>
            <option value="">– select –</option>
            {teamsForSport.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>

        <label style={labelCol}>
          <span>Venue</span>
          <select value={form.venue_id} onChange={(e)=>setForm({...form, venue_id:e.target.value})}>
            <option value="">– none –</option>
            {venues.map(v => <option key={v.id} value={v.id}>{v.name}{v.location ? ` (${v.location})` : ''}</option>)}
          </select>
        </label>

        <label style={labelCol}>
          <span>Date</span>
          <input type="date" value={form.date} onChange={(e)=>setForm({...form, date:e.target.value})} required />
        </label>

        <label style={labelCol}>
          <span>Time</span>
          <input type="time" value={form.time} onChange={(e)=>setForm({...form, time:e.target.value})} required />
        </label>

        <label style={labelCol}>
          <span>Home Score</span>
          <input
            type="number"
            inputMode="numeric"
            pattern="\d*"
            step="1"
            min="0"
            value={form.home_score}
            onChange={(e)=>setForm({...form, home_score:e.target.value})}
            onKeyDown={blockNonIntegerKeys}
            onPaste={preventNonDigitPaste}
            placeholder="(optional)"
          />
        </label>

        <label style={labelCol}>
          <span>Away Score</span>
          <input
            type="number"
            inputMode="numeric"
            pattern="\d*"
            step="1"
            min="0"
            value={form.away_score}
            onChange={(e)=>setForm({...form, away_score:e.target.value})}
            onKeyDown={blockNonIntegerKeys}
            onPaste={preventNonDigitPaste}
            placeholder="(optional)"
          />
        </label>

        <label style={labelCol}>
          <span>Status</span>
          <select value={form.status} onChange={(e)=>setForm({...form, status:e.target.value})}>
            <option value="scheduled">scheduled</option>
            <option value="final">final</option>
          </select>
        </label>

        <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 12 }}>
          <button type="submit">{editingId ? 'Update Game' : 'Create Game'}</button>
          {editingId && <button type="button" onClick={resetForm}>Cancel</button>}
        </div>
      </form>

      {/* Games table */}
      <table style={table}>
        <thead>
          <tr>
            <th style={th}>Date</th><th style={th}>Time</th><th style={th}>Sport</th>
            <th style={th}>Home</th><th style={th}>Away</th><th style={th}>Venue</th>
            <th style={th}>Score</th><th style={th}>Status</th><th style={th}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {games.map(g => (
            <tr key={g.id}>
              <td style={td}>{g.date}</td>
              <td style={td}>{g.time}</td>
              <td style={td}>{lookupName(sports, g.sport_id)}</td>
              <td style={td}>{lookupName(teams, g.home_team_id)}</td>
              <td style={td}>{lookupName(teams, g.away_team_id)}</td>
              <td style={td}>{lookupName(venues, g.venue_id)}</td>
              <td style={td}>{formatScore(g.home_score, g.away_score)}</td>
              <td style={td}>{g.status}</td>
              <td style={td}>
                <button onClick={()=>onEdit(g)} style={{ marginRight: 6 }}>Edit</button>
                <button onClick={()=>onDelete(g.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Report section under games table */}
      <h2 style={{ marginTop: 40 }}>Games Report (filters + stats)</h2>
      <div style={reportBar}>
        <label>From<br/>
          <input type="date" value={reportFilters.from}
            onChange={(e)=>setReportFilters({...reportFilters, from:e.target.value})}/>
        </label>
        <label>To<br/>
          <input type="date" value={reportFilters.to}
            onChange={(e)=>setReportFilters({...reportFilters, to:e.target.value})}/>
        </label>
        <label>Sport<br/>
          <select value={reportFilters.sport_id}
            onChange={(e)=>setReportFilters({ ...reportFilters, sport_id:e.target.value, team_id:'' })}>
            <option value="">(any)</option>
            {sports.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label>Team<br/>
          <select value={reportFilters.team_id}
            onChange={(e)=>setReportFilters({ ...reportFilters, team_id:e.target.value })}
            disabled={!reportFilters.sport_id}>
            <option value="">(any)</option>
            {reportTeams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>
        <div style={{ alignSelf: 'end', display:'flex', gap:8 }}>
          <button onClick={runReport}>Run Report</button>
          <button type="button" onClick={clearReport}>Clear</button>
        </div>
      </div>

      {report && (
        <div style={{ marginTop: 16 }}>
          <div style={statsBox}>
            <div><b>Total games:</b> {report.stats.total_games}</div>
            <div><b>Finals:</b> {report.stats.finals_count}</div>
            <div><b>Avg pts (finals):</b> {fmt(report.stats.avg_points_per_final)}</div>
            <div><b>Win rate (team):</b> {pct(report.stats.win_rate_for_team)}</div>
          </div>

          <table style={table}>
            <thead>
              <tr>
                <th style={th}>Date</th><th style={th}>Time</th><th style={th}>Sport</th>
                <th style={th}>Home</th><th style={th}>Away</th><th style={th}>Status</th><th style={th}>Score</th>
              </tr>
            </thead>
            <tbody>
              {report.rows.map(r => (
                <tr key={r.id}>
                  <td style={td}>{r.date}</td>
                  <td style={td}>{r.time}</td>
                  <td style={td}>{lookupName(sports, r.sport_id)}</td>
                  <td style={td}>{lookupName(teams, r.home_team_id)}</td>
                  <td style={td}>{lookupName(teams, r.away_team_id)}</td>
                  <td style={td}>{r.status}</td>
                  <td style={td}>{formatScore(r.home_score, r.away_score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Helpers
const lookupName = (arr, id) => {
  if (id == null || id === '') return '-'
  const x = arr.find(a => String(a.id) === String(id))
  return x ? (x.name || '-') : '-'
}
const formatScore = (hs, as_) => (hs == null || as_ == null ? '–' : `${hs} - ${as_}`)
const numOrNull = (v) => (v === '' || v == null ? null : Number(v))
const fmt = (x) => (x == null ? '–' : Number(x).toFixed(2))
const pct = (x) => (x == null ? '–' : `${(x*100).toFixed(1)}%`)

// Styles
const page = { fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1100, margin: '0 auto', color: '#f0f0f0', background: '#1e1e1e', minHeight: '100vh' }
const formGrid = { display: 'grid', gridTemplateColumns: 'repeat(4, minmax(180px, 1fr))', gap: 12, marginBottom: 24, alignItems: 'end' }
const labelCol = { display: 'grid', gap: 6 }
const table = { width: '100%', borderCollapse: 'collapse', marginTop: 12 }
const th = { textAlign: 'left', borderBottom: '1px solid #444', padding: '8px' }
const td = { borderBottom: '1px solid #333', padding: '8px' }
const reportBar = { display: 'grid', gridTemplateColumns: 'repeat(5, minmax(160px, 1fr))', gap: 12, alignItems:'end' }
const statsBox = {
  display: 'flex',
  gap: 24,
  padding: '10px 12px',
  background: '#2a2a2a',
  color: '#f0f0f0',
  border: '1px solid #444',
  borderRadius: 8,
  marginTop: 12
}
