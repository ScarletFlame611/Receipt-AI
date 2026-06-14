import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'

export default function ReceiptList() {
  const [receipts, setReceipts] = useState(null)
  const [error, setError] = useState('')

  function load() {
    api.listReceipts().then(setReceipts).catch((e) => setError(e.message))
  }
  useEffect(load, [])

  async function remove(id) {
    if (!confirm('Удалить чек?')) return
    await api.deleteReceipt(id)
    load()
  }

  if (error) return <div className="error">{error}</div>
  if (!receipts) return <div className="muted">Загрузка…</div>

  return (
    <div>
      <div className="row">
        <h2>Мои чеки</h2>
        <Link to="/upload" className="right"><button className="small">+ Загрузить</button></Link>
      </div>
      <div className="card">
        {receipts.length === 0 ? (
          <p className="muted">Пока нет чеков. <Link to="/upload">Загрузите первый</Link>.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Магазин</th><th>Дата</th><th>Сумма</th><th>Позиций</th><th>Статус</th><th></th></tr>
            </thead>
            <tbody>
              {receipts.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/receipts/${r.id}`}>{r.merchant || <span className="muted">—</span>}</Link></td>
                  <td>{r.purchase_date || <span className="muted">—</span>}</td>
                  <td>{r.total != null ? `${r.total} ₽` : <span className="muted">—</span>}</td>
                  <td>{r.items?.length ?? 0}</td>
                  <td><span className={`badge ${r.status}`}>{r.status}</span></td>
                  <td className="row">
                    <Link to={`/receipts/${r.id}`}><button className="ghost small">Править</button></Link>
                    <button className="danger small" onClick={() => remove(r.id)}>Удалить</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
