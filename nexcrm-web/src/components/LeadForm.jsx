import { useState } from 'react'
import TagInput from './TagInput'

const STATUSES = ['New', 'Contacted', 'Qualified', 'ClosedWon', 'ClosedLost']

export default function LeadForm({ initial = {}, contacts = [], onSubmit, onCancel, loading }) {
  const [form, setForm] = useState({
    title: initial.title ?? '',
    contact_id: initial.contact_id ?? '',
    status: initial.status ?? 'New',
    value: initial.value ?? '',
    notes: initial.notes ?? '',
    tags: initial.tags ?? [],
  })
  const [errors, setErrors] = useState({})

  const validate = () => {
    const e = {}
    if (!form.title.trim()) e.title = 'Title is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    const payload = {
      ...form,
      contact_id: form.contact_id ? Number(form.contact_id) : null,
      value: form.value !== '' ? Number(form.value) : null,
      tags: form.tags,
    }
    onSubmit(payload)
  }

  const set = (key) => (e) => { setForm(f => ({ ...f, [key]: e.target.value })); setErrors(er => ({ ...er, [key]: '' })) }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="label">Title <span className="text-red-500">*</span></label>
        <input value={form.title} onChange={set('title')} placeholder="Lead title" className={`input ${errors.title ? 'border-red-400' : ''}`} />
        {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title}</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Status</label>
          <select value={form.status} onChange={set('status')} className="input">
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Deal Value ($)</label>
          <input type="number" min="0" step="0.01" value={form.value} onChange={set('value')} placeholder="0.00" className="input" />
        </div>
      </div>
      <div>
        <label className="label">Contact</label>
        <select value={form.contact_id} onChange={set('contact_id')} className="input">
          <option value="">— None —</option>
          {contacts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Notes</label>
        <textarea value={form.notes} onChange={set('notes')} rows={3} placeholder="Any notes…" className="input resize-none" />
      </div>
      <div>
        <label className="label">Tags</label>
        <TagInput tags={form.tags} onChange={tags => setForm(f => ({ ...f, tags }))} />
        <p className="text-xs text-gray-400 mt-1">Press Enter or comma to add a tag</p>
      </div>
      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary flex-1" disabled={loading}>
          {loading ? 'Saving…' : 'Save Lead'}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
