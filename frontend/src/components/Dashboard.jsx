import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { api } from '../api/client.js'

const COLORS = ['#4f46e5', '#16a34a', '#f59e0b', '#e91e63', '#9c27b0', '#2196f3', '#9e9e9e']

const rub = (v) => `${Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  async function load() {
    try {
      const [summary, timeline, merchants, goods, budgets, categories] = await Promise.all([
        api.summary(), api.timeline(), api.topMerchants(), api.topGoods(),
        api.listBudgets(), api.categories(),
      ])
      setData({ summary, timeline, merchants, goods, budgets, categories })
    } catch (e) {
      setError(e.message)
    }
  }
  useEffect(() => { load() }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="muted">Загрузка…</div>

  const { summary, timeline, merchants, goods } = data
  // «Частые магазины» — те же данные, но по числу чеков, а не по сумме.
  const frequentMerchants = [...merchants].sort((a, b) => b.count - a.count).slice(0, 7)

  return (
    <div>
      <h2>Дашборд</h2>

      {/* KPI */}
      <div className="grid grid-3">
        <div className="card"><div className="muted">Всего потрачено</div><div className="stat">{rub(summary.total)}</div></div>
        <div className="card"><div className="muted">Чеков загружено</div><div className="stat">{summary.receipts_count}</div></div>
        <div className="card"><div className="muted">Категорий с тратами</div><div className="stat">{summary.by_category.length}</div></div>
      </div>

      <div className="grid grid-2">
        {/* Траты по категориям чека */}
        <div className="card">
          <h3>Траты по категориям</h3>
          {summary.by_category.length === 0 ? <p className="muted">Нет данных</p> : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={summary.by_category} dataKey="total" nameKey="category" outerRadius={100} label>
                  {summary.by_category.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => rub(v)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Динамика */}
        <div className="card">
          <h3>Динамика по месяцам</h3>
          {timeline.length === 0 ? <p className="muted">Нет данных</p> : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="period" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip formatter={(v) => rub(v)} />
                <Line type="monotone" dataKey="total" stroke="var(--primary)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Топ магазинов по сумме */}
      <div className="card">
        <h3>Топ магазинов по тратам</h3>
        {merchants.length === 0 ? <p className="muted">Нет данных</p> : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={merchants}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="merchant" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip formatter={(v) => rub(v)} />
              <Bar dataKey="total" fill="var(--primary)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-2">
        {/* Самые частые магазины */}
        <RankList
          title="Самые частые магазины"
          rows={frequentMerchants}
          label={(r) => r.merchant || '—'}
          meta={(r) => `${r.count} чек(ов)`}
          value={(r) => rub(r.total)}
        />

        {/* Самые частые продукты */}
        <RankList
          title="Самые частые продукты"
          rows={goods}
          label={(r) => r.name || '—'}
          meta={(r) => `${r.count} раз`}
          value={(r) => rub(r.total)}
        />
      </div>

      <Budgets data={data} reload={load} />
    </div>
  )
}

function RankList({ title, rows, label, meta, value }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {(!rows || rows.length === 0) ? <p className="muted">Нет данных</p> : (
        <table>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--text-muted)', width: 28 }}>{i + 1}</td>
                <td>{label(r)}<div className="muted" style={{ fontSize: 12 }}>{meta(r)}</div></td>
                <td className="right" style={{ whiteSpace: 'nowrap' }}>{value(r)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function Budgets({ data, reload }) {
  const [limit, setLimit] = useState('')
  const { summary } = data

  // Бюджеты — по категории чека (receipt_type). Тратами считаем сумму по
  // соответствующей категории из сводки, для «общего» бюджета — весь итог.
  const catName = (id) => data.categories.find((c) => c.id === id)?.name
  const spentForCategory = (id) => {
    if (id == null) return summary.total
    const name = catName(id)
    return summary.by_category.find((c) => c.category === name)?.total || 0
  }

  async function add(e) {
    e.preventDefault()
    await api.createBudget({ limit_amount: limit, category_id: null, period: 'monthly' })
    setLimit(''); reload()
  }

  return (
    <div className="card">
      <h3>Бюджеты</h3>
      {data.budgets.map((b) => {
        const spent = spentForCategory(b.category_id)
        const limitNum = Number(b.limit_amount)
        const pct = limitNum > 0 ? Math.min(100, (spent / limitNum) * 100) : 0
        const over = spent > limitNum
        return (
          <div key={b.id} style={{ marginBottom: 12 }}>
            <div className="row" style={{ fontSize: 14 }}>
              <span>{b.category_id == null ? 'Общий' : catName(b.category_id) || `#${b.category_id}`}</span>
              <span className="right">{rub(spent)} / {rub(limitNum)}</span>
              <button className="ghost small" onClick={async () => { await api.deleteBudget(b.id); reload() }}>✕</button>
            </div>
            <div className="progress"><span className={over ? 'over' : ''} style={{ width: `${pct}%` }} /></div>
          </div>
        )
      })}
      {data.budgets.length === 0 && <p className="muted">Бюджеты не заданы.</p>}

      <form className="row" onSubmit={add} style={{ marginTop: 12 }}>
        <input type="number" step="0.01" placeholder="Месячный лимит, ₽" value={limit} onChange={(e) => setLimit(e.target.value)} required />
        <button className="small" type="submit">Добавить</button>
      </form>
    </div>
  )
}
