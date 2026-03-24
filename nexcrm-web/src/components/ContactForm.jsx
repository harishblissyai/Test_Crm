import { useState } from 'react'
import TagInput from './TagInput'

export default function ContactForm({ initial = {}, onSubmit, onCancel, loading }) {
  const [form, setForm] = useState({
    name: initial.name ?? '',
    email: initial.email ?? '',
    phone: initial.phone ?? '',
    company: initial.company ?? '',
    notes: initial.notes ?? '',
    tags: initial.tags ?? [],
  })
  const [errors, setErrors] = useState({})

  const validate = () => {
    const e = {}
    if (!form.name.trim()) e.name = 'Name is required'
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Invalid email'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (validate()) onSubmit(form)
  }

  const field = (key) => ({
    value: form[key],
    onChange: (e) => { setForm(f => ({ ...f, [key]: e.target.value })); setErrors(er => ({ ...er, [key]: '' })) },
    className: `input ${errors[key] ? 'border-red-400 focus:border-red-400 focus:ring-red-300' : ''}`,
  })

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="label">Name <span className="text-red-500">*</span></label>
        <input {...field('name')} placeholder="Full name" />
        {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Email</label>
          <input type="email" {...field('email')} placeholder="email@company.com" />
          {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email}</p>}
        </div>
        <div>
          <label className="label">Phone</label>
          <input {...field('phone')} placeholder="+1 234 567 8900" />
        </div>
      </div>
      <div>
        <label className="label">Company</label>
        <input {...field('company')} placeholder="Company name" />
      </div>
      <div>
        <label className="label">Notes</label>
        <textarea {...field('notes')} rows={3} placeholder="Any notes…" className={`input resize-none ${errors.notes ? 'border-red-400' : ''}`} />
      </div>
      <div>
        <label className="label">Tags</label>
        <TagInput tags={form.tags} onChange={tags => setForm(f => ({ ...f, tags }))} />
        <p className="text-xs text-gray-400 mt-1">Press Enter or comma to add a tag</p>
      </div>
      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary flex-1" disabled={loading}>
          {loading ? 'Saving…' : 'Save Contact'}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
