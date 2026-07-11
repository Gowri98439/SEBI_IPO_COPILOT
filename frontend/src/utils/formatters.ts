import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns'

/* ── Date formatting ──────────────────────────────────────────────────── */
export function formatDate(date: string | Date): string {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(d)) return '—'
    return format(d, 'dd MMM yyyy')
  } catch {
    return '—'
  }
}

export function formatDateTime(date: string | Date): string {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(d)) return '—'
    return format(d, 'dd MMM yyyy, HH:mm')
  } catch {
    return '—'
  }
}

export function formatRelativeTime(date: string | Date): string {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(d)) return '—'
    return formatDistanceToNow(d, { addSuffix: true })
  } catch {
    return '—'
  }
}

/* ── File size ────────────────────────────────────────────────────────── */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const value = bytes / Math.pow(k, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

/* ── Score formatting ─────────────────────────────────────────────────── */
export function formatScore(score: number): string {
  return `${Math.round(score)}%`
}

export function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-400'
  if (score >= 60) return 'text-amber-400'
  if (score >= 40) return 'text-orange-400'
  return 'text-red-400'
}

export function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-500'
  if (score >= 60) return 'bg-amber-500'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-red-500'
}

/* ── Severity colors ──────────────────────────────────────────────────── */
export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'high':
      return 'text-red-400'
    case 'medium':
      return 'text-amber-400'
    case 'low':
      return 'text-blue-400'
    default:
      return 'text-gray-500'
  }
}

export function getSeverityBadgeClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'high':
      return 'bg-red-500/15 text-red-400 border border-red-500/20'
    case 'medium':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
    case 'low':
      return 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
    default:
      return 'bg-gray-100 text-gray-600 border border-gray-200'
  }
}

/* ── Status colors ────────────────────────────────────────────────────── */
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'pass':
    case 'validated':
    case 'completed':
    case 'approved':
      return 'text-emerald-400'
    case 'fail':
    case 'failed':
    case 'rejected':
      return 'text-red-400'
    case 'warning':
    case 'pending':
    case 'in_review':
      return 'text-amber-400'
    case 'running':
    case 'validating':
    case 'processing':
      return 'text-blue-400'
    case 'draft':
    case 'active':
      return 'text-violet-400'
    default:
      return 'text-gray-500'
  }
}

export function getStatusBadgeClass(status: string): string {
  switch (status.toLowerCase()) {
    case 'pass':
    case 'validated':
    case 'completed':
    case 'approved':
      return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
    case 'fail':
    case 'failed':
    case 'rejected':
      return 'bg-red-500/15 text-red-400 border border-red-500/20'
    case 'warning':
    case 'pending':
    case 'in_review':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
    case 'running':
    case 'validating':
    case 'processing':
      return 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
    case 'draft':
    case 'active':
      return 'bg-violet-500/15 text-violet-400 border border-violet-500/20'
    default:
      return 'bg-gray-100 text-gray-600 border border-gray-200'
  }
}

/* ── Status icon name ─────────────────────────────────────────────────── */
export function getStatusIcon(status: string): string {
  switch (status.toLowerCase()) {
    case 'pass':
    case 'validated':
    case 'completed':
    case 'approved':
      return 'CheckCircle'
    case 'fail':
    case 'failed':
    case 'rejected':
      return 'XCircle'
    case 'warning':
      return 'AlertTriangle'
    case 'pending':
    case 'in_review':
      return 'Clock'
    case 'running':
    case 'validating':
    case 'processing':
      return 'Loader2'
    case 'draft':
      return 'FileText'
    case 'active':
      return 'Activity'
    default:
      return 'Circle'
  }
}

/* ── Number formatting ────────────────────────────────────────────────── */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-IN').format(n)
}

export function formatCurrency(n: number, currency = 'INR'): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(n)
}

/* ── Truncation ───────────────────────────────────────────────────────── */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - 3) + '...'
}

/* ── Initials ─────────────────────────────────────────────────────────── */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}
