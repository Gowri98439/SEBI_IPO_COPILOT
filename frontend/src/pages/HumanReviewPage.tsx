import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { ClipboardList, Plus, CheckCircle2, Clock, AlertCircle, User, Calendar } from 'lucide-react'
import { useReviewTasks, useCreateReviewTask } from '@/api/reviews'
import { apiClient } from '@/api/client'
import { formatDate } from '@/utils/formatters'

type FilterStatus = 'all' | 'open' | 'in_progress' | 'completed'

const STATUS_CONFIG = {
  open: { icon: Clock, color: 'text-ipo-attention', bg: 'bg-ipo-attention/10', border: 'border-ipo-attention/30', label: 'Open' },
  in_progress: { icon: AlertCircle, color: 'text-ipo-ai', bg: 'bg-ipo-ai/10', border: 'border-ipo-ai/30', label: 'In Progress' },
  completed: { icon: CheckCircle2, color: 'text-ipo-verified', bg: 'bg-ipo-verified/10', border: 'border-ipo-verified/30', label: 'Completed' },
}

const TASK_TYPES = ['validate', 'approve', 'reject', 'request_changes']

export default function HumanReviewPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [showCreate, setShowCreate] = useState(false)
  const [newTask, setNewTask] = useState({ task_type: 'validate', notes: '', assigned_to: '' })

  const { data: tasks = [], refetch } = useReviewTasks(workspaceId!)
  const createTask = useCreateReviewTask()

  const filtered = filter === 'all' ? tasks : tasks.filter((t) => t.status === filter)

  const handleCreate = async () => {
    await createTask.mutateAsync({
      workspace_id: workspaceId!,
      ...newTask,
      assigned_to: newTask.assigned_to.trim() || undefined,
    } as any)
    setShowCreate(false)
    setNewTask({ task_type: 'validate', notes: '', assigned_to: '' })
    refetch()
  }

  const handleStatusChange = async (taskId: string, status: string) => {
    try {
      await apiClient.patch(`/reviews/${taskId}`, { status })
      refetch()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="p-6 space-y-6 font-body">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display text-ipo-text mb-1">Human Review Workflow</h1>
          <p className="text-ipo-text-secondary text-sm">Manage review tasks and approval workflow for IPO documents</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-ipo-text text-ipo-base hover:bg-ipo-text-secondary text-sm font-semibold px-4 py-2 rounded-md transition-colors"
        >
          <Plus className="w-4 h-4" /> Create Task
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { ...STATUS_CONFIG.open, label: 'Open Tasks', value: tasks.filter((t) => t.status === 'open').length },
          { ...STATUS_CONFIG.in_progress, label: 'In Progress', value: tasks.filter((t) => t.status === 'in_progress').length },
          { ...STATUS_CONFIG.completed, label: 'Completed', value: tasks.filter((t) => t.status === 'completed').length },
        ].map((s) => (
          <div key={s.label} className={`bg-ipo-elevated border border-ipo-border rounded-xl p-5 shadow-sm`}>
            <div className={`w-8 h-8 ${s.bg} rounded-md flex items-center justify-center mb-3`}>
              <s.icon className={`w-4 h-4 ${s.color}`} />
            </div>
            <p className="text-3xl font-bold font-display text-ipo-text">{s.value}</p>
            <p className="text-ipo-text-secondary text-sm mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(['all', 'open', 'in_progress', 'completed'] as FilterStatus[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-md text-sm font-semibold transition-colors capitalize border ${
              filter === f
                ? 'bg-ipo-text border-ipo-text text-ipo-base'
                : 'bg-ipo-overlay border-ipo-border text-ipo-text-secondary hover:text-ipo-text'
            }`}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Task List */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 bg-ipo-elevated border border-ipo-border rounded-xl border-dashed">
          <ClipboardList className="w-10 h-10 text-ipo-text-secondary mx-auto mb-3" />
          <p className="text-ipo-text-secondary text-sm">No review tasks yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((task) => {
            const cfg = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.open
            return (
              <div
                key={task.id}
                className="bg-ipo-elevated border border-ipo-border hover:border-ipo-text-secondary rounded-xl p-5 transition-colors shadow-sm"
              >
                <div className="flex items-start gap-4">
                  <div className={`w-10 h-10 ${cfg.bg} border ${cfg.border} rounded-md flex items-center justify-center flex-shrink-0`}>
                    <cfg.icon className={`w-5 h-5 ${cfg.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-ipo-text font-semibold capitalize text-sm">
                        {task.task_type.replace('_', ' ')}
                      </p>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider font-data ${cfg.bg} ${cfg.color} ${cfg.border}`}>
                        {cfg.label}
                      </span>
                    </div>
                    {task.notes && <p className="text-ipo-text-secondary text-sm">{task.notes}</p>}
                    <div className="flex items-center gap-4 mt-3">
                      {task.assigned_to && (
                        <div className="flex items-center gap-1.5 text-ipo-text-secondary text-xs">
                          <User className="w-3.5 h-3.5" />
                          <span className="font-data">{task.assigned_to.slice(0, 8)}...</span>
                        </div>
                      )}
                      {task.due_date && (
                        <div className="flex items-center gap-1.5 text-ipo-text-secondary text-xs font-data">
                          <Calendar className="w-3.5 h-3.5" />
                          {formatDate(task.due_date)}
                        </div>
                      )}
                      <span className="text-ipo-text-secondary text-xs font-data">Created {formatDate(task.created_at)}</span>
                    </div>
                  </div>
                  {task.status !== 'completed' && (
                    <div className="flex gap-2 flex-shrink-0">
                      {task.status === 'open' && (
                        <button
                          onClick={() => handleStatusChange(task.id, 'in_progress')}
                          className="text-xs bg-ipo-overlay hover:bg-ipo-border/50 border border-ipo-border text-ipo-text px-3 py-1.5 rounded-md transition-colors font-semibold"
                        >
                          Start
                        </button>
                      )}
                      <button
                        onClick={() => handleStatusChange(task.id, 'completed')}
                        className="text-xs bg-ipo-verified text-ipo-base hover:bg-ipo-verified/90 px-3 py-1.5 rounded-md transition-colors font-semibold flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3 h-3" /> Complete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create Task Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-ipo-base/80 flex items-center justify-center z-50 p-6 backdrop-blur-sm">
          <div className="bg-ipo-elevated border border-ipo-border rounded-xl p-6 w-full max-w-md space-y-5 shadow-panel">
            <h3 className="text-ipo-text font-display font-semibold text-lg">Create Review Task</h3>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary mb-1.5 font-data">Task Type</label>
              <select
                value={newTask.task_type}
                onChange={(e) => setNewTask((p) => ({ ...p, task_type: e.target.value }))}
                className="input-base w-full"
              >
                {TASK_TYPES.map((t) => (
                  <option key={t} value={t} className="bg-ipo-elevated">
                    {t.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary mb-1.5 font-data">Notes</label>
              <textarea
                value={newTask.notes}
                onChange={(e) => setNewTask((p) => ({ ...p, notes: e.target.value }))}
                placeholder="Add review notes or instructions..."
                rows={3}
                className="input-base w-full resize-none"
              />
            </div>

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 bg-ipo-overlay hover:bg-ipo-border/50 border border-ipo-border text-ipo-text font-semibold py-2.5 rounded-md transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createTask.isPending}
                className="flex-1 bg-ipo-text text-ipo-base hover:bg-ipo-text-secondary font-semibold py-2.5 rounded-md transition-colors disabled:opacity-60 text-sm"
              >
                {createTask.isPending ? 'Creating...' : 'Create Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
