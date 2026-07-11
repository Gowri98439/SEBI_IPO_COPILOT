import * as RadixDialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface ModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title?: string
  description?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  showClose?: boolean
  className?: string
}

const SIZE_CLASSES = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
  full: 'max-w-5xl',
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  size = 'md',
  showClose = true,
  className,
}: ModalProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        {/* Backdrop */}
        <RadixDialog.Overlay
          className="fixed inset-0 z-50 bg-gray-900/40 backdrop-blur-sm
                     data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out"
        />

        {/* Content */}
        <RadixDialog.Content
          className={cn(
            'fixed left-1/2 top-1/2 z-50 w-full -translate-x-1/2 -translate-y-1/2',
            'bg-white border border-gray-200 rounded-2xl shadow-panel',
            'p-6 focus:outline-none',
            'data-[state=open]:animate-slide-up data-[state=closed]:animate-fade-out',
            SIZE_CLASSES[size],
            className
          )}
        >
          {/* Header */}
          {(title ?? description ?? showClose) && (
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                {title && (
                  <RadixDialog.Title className="text-lg font-semibold text-gray-900">
                    {title}
                  </RadixDialog.Title>
                )}
                {description && (
                  <RadixDialog.Description className="mt-1 text-sm text-gray-500">
                    {description}
                  </RadixDialog.Description>
                )}
              </div>
              {showClose && (
                <RadixDialog.Close
                  className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg
                             text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
                >
                  <X className="h-4 w-4" />
                </RadixDialog.Close>
              )}
            </div>
          )}

          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}

export const ModalTrigger = RadixDialog.Trigger
export const ModalClose = RadixDialog.Close

export default Modal
