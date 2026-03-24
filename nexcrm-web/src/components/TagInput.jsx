import { useState } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'

// Deterministic color from tag text
const TAG_COLORS = [
  'bg-blue-100 text-blue-700 ring-blue-300',
  'bg-purple-100 text-purple-700 ring-purple-300',
  'bg-green-100 text-green-700 ring-green-300',
  'bg-yellow-100 text-yellow-700 ring-yellow-300',
  'bg-pink-100 text-pink-700 ring-pink-300',
  'bg-indigo-100 text-indigo-700 ring-indigo-300',
  'bg-orange-100 text-orange-700 ring-orange-300',
  'bg-teal-100 text-teal-700 ring-teal-300',
]

export function tagColor(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) hash = (hash * 31 + tag.charCodeAt(i)) & 0xffff
  return TAG_COLORS[hash % TAG_COLORS.length]
}

export function TagBadge({ tag, onRemove }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${tagColor(tag)}`}>
      {tag}
      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(tag)}
          className="hover:opacity-70 ml-0.5"
        >
          <XMarkIcon className="h-3 w-3" />
        </button>
      )}
    </span>
  )
}

export default function TagInput({ tags = [], onChange }) {
  const [input, setInput] = useState('')

  function addTag(raw) {
    const tag = raw.trim().toLowerCase().replace(/\s+/g, '-')
    if (!tag || tags.includes(tag)) return
    onChange([...tags, tag])
    setInput('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(input)
    } else if (e.key === 'Backspace' && !input && tags.length) {
      onChange(tags.slice(0, -1))
    }
  }

  function removeTag(tag) {
    onChange(tags.filter(t => t !== tag))
  }

  return (
    <div className="flex flex-wrap gap-1.5 p-2 border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-primary-300 focus-within:border-primary-400 bg-white min-h-[42px]">
      {tags.map(t => (
        <TagBadge key={t} tag={t} onRemove={removeTag} />
      ))}
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => input && addTag(input)}
        placeholder={tags.length ? '' : 'Add tags (Enter or comma to add)'}
        className="flex-1 min-w-[120px] outline-none text-sm bg-transparent text-gray-700 placeholder-gray-400"
      />
    </div>
  )
}
