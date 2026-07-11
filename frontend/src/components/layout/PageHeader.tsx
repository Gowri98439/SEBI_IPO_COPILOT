import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface PageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
  className?: string
  badge?: ReactNode
}

export default function PageHeader({
  title,
  description,
  action,
  className,
  badge,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'mb-6 flex flex-col gap-1 border-b border-slate-800/60 pb-5 sm:flex-row sm:items-start sm:justify-between',
        className
      )}
    >
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight text-slate-50">{title}</h2>
          {badge && <span>{badge}</span>}
        </div>
        {description && (
          <p className="max-w-2xl text-sm text-gray-500">{description}</p>
        )}
      </div>

      {action && <div className="mt-2 flex flex-shrink-0 items-center gap-2 sm:mt-0">{action}</div>}
    </div>
  )
}
