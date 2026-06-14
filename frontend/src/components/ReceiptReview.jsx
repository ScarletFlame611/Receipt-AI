import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'

// Поля шапки, которые важно заполнить — по ним подсвечиваем пустоты.
const REQUIRED_HEADER = ['merchant', 'purchase_date', 'total']

const emptyItem = () => ({ name: '', good: '', brand: '', quantity: '', price: '', category_id: '' })

export default function ReceiptReview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [receipt, setReceipt] = useState(null)
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    Promise.all([api.getReceipt(id), api.categories()])
      .then(([r, cats]) => {
        setReceipt({
          ...r,
          merchant: r.merchant || '',
          purchase_date: r.purchase_date || '',
          total: r.total ?? '',
          receipt_type: r.receipt_type || '',
          items: (r.items || []).map((it) => ({
            name: it.name || '',
            good: it.good || '',
            brand: it.brand || '',
            quantity: it.quantity ?? '',
            price: it.price ?? '',
            category_id: it.category_id ?? '',
          })),
        })
        setCategories(cats)
      })
      .catch((e) => setError(e.message))
  }, [id])

  if (error) return <div className="error">{error}</div>
  if (!receipt) return <div className="muted">Загрузка…</div>

  const setField = (k, v) => { setReceipt((r) => ({ ...r, [k]: v })); setSaved(false) }
  const setItem = (i, k, v) =>
    setReceipt((r) => {
      const items = r.items.slice()
      items[i] = { ...items[i], [k]: v }
      return { ...r, items }
    })
  const addItem = () => setReceipt((r) => ({ ...r, items: [...r.items, emptyItem()] }))
  const removeItem = (i) =>
    setReceipt((r) => ({ ...r, items: r.items.filter((_, idx) => idx !== i) }))

  const isEmpty = (v) => v === '' || v === null || v === undefined
  const emptyCount =
    REQUIRED_HEADER.filter((k) => isEmpty(receipt[k])).length +
    receipt.items.filter((it) => isEmpty(it.name) || isEmpty(it.price)).length

  async function save() {
    setBusy(true)
    setError('')
    try {
      const payload = {
        merchant: receipt.merchant || null,
        purchase_date: receipt.purchase_date || null,
        total: receipt.total === '' ? null : receipt.total,
        receipt_type: receipt.receipt_type || null,
        status: emptyCount > 0 ? 'needs_review' : 'ok',
        items: receipt.items
          .filter((it) => it.name.trim())
          .map((it) => ({
            name: it.name,
            good: it.good || null,
            brand: it.brand || null,
            quantity: it.quantity === '' ? null : it.quantity,
            price: it.price === '' ? null : it.price,
            category_id: it.category_id === '' ? null : Number(it.category_id),
          })),
      }
      const updated = await api.reviewReceipt(id, payload)
      setSaved(true)
      setReceipt((r) => ({ ...r, status: updated.status }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!confirm('Удалить чек?')) return
    await api.deleteReceipt(id)
    navigate('/receipts')
  }

  const cls = (v) => (isEmpty(v) ? 'field empty-field' : 'field')

  return (
    <div>
      <div className="row">
        <h2>Проверка чека #{receipt.id}</h2>
        <span className={`badge ${receipt.status} right`}>{receipt.status}</span>
      </div>
      {emptyCount > 0 && (
        <div className="error">
          Не заполнено полей: {emptyCount}. Подсвеченные поля стоит проверить.
        </div>
      )}

      <div className="card">
        <div className="grid grid-2">
          <div className={cls(receipt.merchant)}>
            <label>Магазин</label>
            <input value={receipt.merchant} onChange={(e) => setField('merchant', e.target.value)} />
          </div>
          <div className={cls(receipt.purchase_date)}>
            <label>Дата покупки</label>
            <input type="date" value={receipt.purchase_date} onChange={(e) => setField('purchase_date', e.target.value)} />
          </div>
          <div className={cls(receipt.total)}>
            <label>Сумма</label>
            <input type="number" step="0.01" value={receipt.total} onChange={(e) => setField('total', e.target.value)} />
          </div>
          <div className="field">
            <label>Категория чека</label>
            <input value={receipt.receipt_type} onChange={(e) => setField('receipt_type', e.target.value)} />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="row">
          <h3>Позиции</h3>
          <button className="ghost small right" onClick={addItem}>+ Добавить</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Название</th><th>Товар</th><th>Бренд</th><th>Кол-во</th><th>Цена</th><th>Категория</th><th></th>
            </tr>
          </thead>
          <tbody>
            {receipt.items.map((it, i) => (
              <tr key={i}>
                <td><input className={isEmpty(it.name) ? 'empty-field' : ''} value={it.name} onChange={(e) => setItem(i, 'name', e.target.value)} /></td>
                <td><input value={it.good} onChange={(e) => setItem(i, 'good', e.target.value)} /></td>
                <td><input value={it.brand} onChange={(e) => setItem(i, 'brand', e.target.value)} /></td>
                <td><input type="number" step="0.001" value={it.quantity} onChange={(e) => setItem(i, 'quantity', e.target.value)} /></td>
                <td><input className={isEmpty(it.price) ? 'empty-field' : ''} type="number" step="0.01" value={it.price} onChange={(e) => setItem(i, 'price', e.target.value)} /></td>
                <td>
                  <select value={it.category_id} onChange={(e) => setItem(i, 'category_id', e.target.value)}>
                    <option value="">—</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </td>
                <td><button className="ghost small" onClick={() => removeItem(i)}>✕</button></td>
              </tr>
            ))}
            {receipt.items.length === 0 && (
              <tr><td colSpan={7} className="muted">Позиции не распознаны — добавьте вручную.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {error && <div className="error">{error}</div>}
      {saved && <div className="success-msg">Сохранено.</div>}
      <div className="row">
        <button onClick={save} disabled={busy}>{busy ? 'Сохранение…' : 'Сохранить'}</button>
        <button className="ghost" onClick={() => navigate('/receipts')}>К списку</button>
        <button className="danger right" onClick={remove}>Удалить</button>
      </div>
    </div>
  )
}
