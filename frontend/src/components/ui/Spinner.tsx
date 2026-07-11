import { cn } from '@/utils/cn'

interface SpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  label?: string
  variant?: 'primary' | 'white' | 'muted'
}

const SIZE_CLASSES = {
  xs: 'h-3 w-3 border',
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-2',
  xl: 'h-12 w-12 border-[3px]',
}

const VARIANT_CLASSES = {
  primary: 'border-primary-600 border-t-primary-300',
  white: 'border-white/30 border-t-white',
  muted: 'border-slate-700 border-t-slate-400',
}

export function Spinner({ size = 'md', className, label, variant = 'primary' }: SpinnerProps) {
  return (
    <div
      role="status"
      className={cn('inline-flex flex-col items-center gap-2', className)}
    >
      <div
        className={cn(
          'animate-spin rounded-full',
          SIZE_CLASSES[size],
          VARIANT_CLASSES[variant]
        )}
      />
      {label && (
        <span className="text-xs text-gray-500">{label}</span>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function SpinnerOverlay({ label }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[200px] w-full items-center justify-center">
      <Spinner size="lg" label={label} />
    </div>
  )
}

export default Spinner
