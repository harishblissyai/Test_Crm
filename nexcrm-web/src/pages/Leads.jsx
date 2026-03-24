import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusIcon, PencilIcon, TrashIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'
import { leadsApi } from '../api/leads'
import { contactsApi } from '../api/contacts'
import DataTable from '../components/DataTable'
import Modal from '../components/Modal'
import LeadForm from '../components/LeadForm'
import { TagBadge } from '../components/TagInput'
import toast from 'react-hot-toast'

const STATUS_COLORS = {
  New: 'bg-gray-100 text-gray-700',
  Contacted: 'bg-blue-100 text-blue-700',
  Qualified: 'bg-yellow-100 text-yellow-700',
  ClosedWon: 'bg-green-100 text-green-700',
  ClosedLost: 'bg-red-100 text-red-700',
}

const STATUSES = ['', 'New', 'Contacted', 'Qualified', 'ClosedWon', 'ClosedLost']

export default function Leads() {
  const navigate = useNavigate()
  const [data, setData] = useState({ items: [], total: 0, pages: 1 })
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving] = useState(false)

  const load = (p = page, s = statusFilter, t = tagFilter) => {
    setLoading(true)
    leadsApi.list({ page: p, size: 20, status: s || undefined, tag: t || undefined })
      .then(setData)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(); contactsApi.list({ size: 100 }).then(r => setContacts(r.items)) }, [])
  useEffect(() => { load() }, [page, statusFilter, tagFilter])

  const handleSave = async (form) => {
    setSaving(true)
    try {
      if (editing) { await leadsApi.update(editing.id, form); toast.success('Lead updated') }
      else { await leadsApi.create(form); toast.success('Lead created') }
      setShowModal(false); setEditing(null); load()
    } catch { toast.error('Failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this lead?')) return
    try { await leadsApi.delete(id); toast.success('Deleted'); load() }
    catch { toast.error('Failed') }
  }

  const columns = [
    { key: 'title', label: 'Title', render: r => <button onClick={() => navigate(`/leads/${r.id}`)} className="font-medium text-primary-600 hover:underline text-left">{r.title}</button> },
    { key: 'status', label: 'Status', render: r => <span className={`badge ${STATUS_COLORS[r.status]}`}>{r.status}</span> },
    { key: 'value', label: 'Value', render: r => r.value != null ? `$${r.value.toLocaleString()}` : <span className="text-gray-400">—</span> },
    { key: 'tags', label: 'Tags', render: r => r.tags?.length ? <div className="flex flex-wrap gap-1">{r.tags.map(t => <TagBadge key={t} tag={t} />)}</div> : <span className="text-gray-400">—</span> },
    { key: 'created_at', label: 'Created', render: r => new Date(r.created_at).toLocaleDateString() },
    { key: 'actions', label: '', render: r => (
      <div className="flex gap-1 justify-end">
        <button onClick={() => { setEditing(r); setShowModal(true) }} className="btn-secondary p-1.5"><PencilIcon className="h-4 w-4" /></button>
        <button onClick={() => handleDelete(r.id)} className="btn p-1.5 text-red-500 hover:bg-red-50 border border-gray-300 rounded-lg"><TrashIcon className="h-4 w-4" /></button>
      </div>
    )},
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
          <p className="text-sm text-gray-500">{data.total} total</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => leadsApi.exportCsv()}>
            <ArrowDownTrayIcon className="h-4 w-4" /> Export CSV
          </button>
          <button className="btn-primary" onClick={() => { setEditing(null); setShowModal(true) }}>
            <PlusIcon className="h-4 w-4" /> New Lead
          </button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        {STATUSES.map(s => (
          <button key={s} onClick={() => { setStatusFilter(s); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${statusFilter === s ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>
            {s || 'All'}
          </button>
        ))}
        <div className="ml-2 flex items-center gap-2">
          <input
            value={tagFilter}
            onChange={e => { setTagFilter(e.target.value); setPage(1) }}
            placeholder="Filter by tag…"
            className="input w-36 text-sm py-1.5"
          />
          {tagFilter && (
            <button onClick={() => { setTagFilter(''); setPage(1) }} className="text-xs text-gray-500 hover:text-gray-700 underline">
              Clear
            </button>
          )}
        </div>
      </div>

      <DataTable columns={columns} data={data.items} loading={loading} page={page} pages={data.pages} onPageChange={setPage} emptyMessage="No leads yet." />

      {showModal && (
        <Modal title={editing ? 'Edit Lead' : 'New Lead'} onClose={() => { setShowModal(false); setEditing(null) }}>
          <LeadForm initial={editing ?? {}} contacts={contacts} onSubmit={handleSave} onCancel={() => { setShowModal(false); setEditing(null) }} loading={saving} />
        </Modal>
      )}
    </div>
  )
}
