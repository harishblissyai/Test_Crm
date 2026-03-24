import { useState, useEffect } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useDroppable } from '@dnd-kit/core'
import { leadsApi } from '../api/leads'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'

const STATUSES = [
  { key: 'New',        label: 'New',          color: 'bg-gray-100 border-gray-300',       badge: 'bg-gray-200 text-gray-700' },
  { key: 'Contacted',  label: 'Contacted',     color: 'bg-blue-50 border-blue-300',        badge: 'bg-blue-100 text-blue-700' },
  { key: 'Qualified',  label: 'Qualified',     color: 'bg-yellow-50 border-yellow-300',    badge: 'bg-yellow-100 text-yellow-700' },
  { key: 'ClosedWon',  label: 'Closed Won',    color: 'bg-green-50 border-green-300',      badge: 'bg-green-100 text-green-700' },
  { key: 'ClosedLost', label: 'Closed Lost',   color: 'bg-red-50 border-red-300',          badge: 'bg-red-100 text-red-700' },
]

function LeadCard({ lead, isDragging }) {
  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 p-3 shadow-sm cursor-grab active:cursor-grabbing transition-shadow ${
        isDragging ? 'shadow-xl opacity-80 rotate-1' : 'hover:shadow-md'
      }`}
    >
      <Link
        to={`/leads/${lead.id}`}
        className="font-medium text-sm text-gray-900 hover:text-primary-600 block truncate"
        onClick={(e) => e.stopPropagation()}
      >
        {lead.title}
      </Link>
      {lead.contact_name && (
        <p className="text-xs text-gray-500 mt-1 truncate">{lead.contact_name}</p>
      )}
      {lead.value && (
        <p className="text-xs font-semibold text-primary-600 mt-2">
          ${Number(lead.value).toLocaleString()}
        </p>
      )}
    </div>
  )
}

function SortableCard({ lead }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
  })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <LeadCard lead={lead} />
    </div>
  )
}

function Column({ status, leads }) {
  const { setNodeRef, isOver } = useDroppable({ id: status.key })
  const total = leads.reduce((sum, l) => sum + (l.value || 0), 0)

  return (
    <div className={`flex flex-col rounded-xl border-2 ${status.color} min-h-[500px] w-64 shrink-0`}>
      {/* Header */}
      <div className="px-3 pt-3 pb-2 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${status.badge}`}>
            {status.label}
          </span>
          <span className="text-xs text-gray-500 font-medium">{leads.length}</span>
        </div>
        {total > 0 && (
          <p className="text-xs text-gray-400 mt-1">${Number(total).toLocaleString()} total</p>
        )}
      </div>

      {/* Cards */}
      <div
        ref={setNodeRef}
        className={`flex-1 p-2 space-y-2 transition-colors rounded-b-xl ${isOver ? 'bg-primary-50' : ''}`}
      >
        <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map((lead) => (
            <SortableCard key={lead.id} lead={lead} />
          ))}
        </SortableContext>
        {leads.length === 0 && (
          <div className="flex items-center justify-center h-20 text-xs text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
            Drop here
          </div>
        )}
      </div>
    </div>
  )
}

export default function Kanban() {
  const [columns, setColumns] = useState(() =>
    Object.fromEntries(STATUSES.map((s) => [s.key, []]))
  )
  const [activeId, setActiveId] = useState(null)
  const [activeLead, setActiveLead] = useState(null)
  const [loading, setLoading] = useState(true)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  useEffect(() => {
    fetchLeads()
  }, [])

  async function fetchLeads() {
    try {
      setLoading(true)
      const res = await leadsApi.list({ size: 200 })
      const grouped = Object.fromEntries(STATUSES.map((s) => [s.key, []]))
      res.data.items.forEach((lead) => {
        if (grouped[lead.status]) grouped[lead.status].push(lead)
      })
      setColumns(grouped)
    } catch {
      toast.error('Failed to load leads')
    } finally {
      setLoading(false)
    }
  }

  function findContainer(id) {
    for (const [key, leads] of Object.entries(columns)) {
      if (leads.find((l) => l.id === id)) return key
    }
    return null
  }

  function handleDragStart({ active }) {
    setActiveId(active.id)
    const container = findContainer(active.id)
    setActiveLead(columns[container]?.find((l) => l.id === active.id) || null)
  }

  async function handleDragEnd({ active, over }) {
    setActiveId(null)
    setActiveLead(null)
    if (!over) return

    const fromCol = findContainer(active.id)
    const toCol = STATUSES.find((s) => s.key === over.id)?.key || findContainer(over.id)

    if (!fromCol || !toCol || fromCol === toCol) return

    // Optimistic update
    const lead = columns[fromCol].find((l) => l.id === active.id)
    setColumns((prev) => ({
      ...prev,
      [fromCol]: prev[fromCol].filter((l) => l.id !== active.id),
      [toCol]: [...prev[toCol], { ...lead, status: toCol }],
    }))

    try {
      await leadsApi.updateStatus(active.id, toCol)
      toast.success(`Moved to ${STATUSES.find((s) => s.key === toCol)?.label}`)
    } catch {
      toast.error('Failed to update status')
      fetchLeads() // revert
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Lead Pipeline</h1>
        <p className="text-sm text-gray-500 mt-1">Drag and drop leads to update their status</p>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STATUSES.map((status) => (
            <Column key={status.key} status={status} leads={columns[status.key]} />
          ))}
        </div>

        <DragOverlay>
          {activeLead ? <LeadCard lead={activeLead} isDragging /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
