import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'

export default function UploadReceipt() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function pick(e) {
    const f = e.target.files?.[0]
    setFile(f || null)
    setError('')
    setPreview(f ? URL.createObjectURL(f) : null)
  }

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const receipt = await api.uploadReceipt(file)
      // Сразу ведём на правку распознанного — ключевой шаг проверки.
      navigate(`/receipts/${receipt.id}`)
    } catch (err) {
      setError(err.message || 'Не удалось загрузить чек')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h2>Загрузка чека</h2>
      <form className="card" onSubmit={submit}>
        <div className="field">
          <label>Фото чека (JPG, PNG, HEIC)</label>
          <input type="file" accept="image/*,.heic" onChange={pick} />
        </div>
        {preview && (
          <img
            src={preview}
            alt="превью"
            style={{ maxHeight: 320, borderRadius: 8, marginBottom: 14, display: 'block' }}
          />
        )}
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={!file || busy}>
          {busy ? 'Распознаём…' : 'Загрузить и распознать'}
        </button>
      </form>
    </div>
  )
}
