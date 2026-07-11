import * as RadixSelect from '@radix-ui/react-select'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

export interface SelectProps {
  label?: string
  error?: string
  hint?: string
  placeholder?: string
  options: SelectOption[]
  value?: string
  onValueChange?: (value: string) => void
  disabled?: boolean
  required?: boolean
  containerClassName?: string
  className?: string
  triggerIcon?: ReactNode
}

export function Select({
  label,
  error,
  hint,
  placeholder = 'Select an option',
  options,
  value,
  onValueChange,
  disabled,
  required,
  containerClassName,
  className,
}: SelectProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', containerClassName)}>
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
          {required && <span className="ml-1 text-red-500">*</span>}
        </label>
      )}

      <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
        <RadixSelect.Trigger
          className={cn(
            'input-base flex items-center justify-between gap-2 cursor-pointer',
            'data-[placeholder]:text-gray-400',
            error && 'border-red-500/60 focus:ring-red-500/40',
            className
          )}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown className="h-4 w-4 text-gray-400" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>

        <RadixSelect.Portal>
          <RadixSelect.Content
            className="z-50 min-w-[180px] overflow-hidden rounded-xl bg-white border border-gray-200 shadow-panel animate-slide-down"
            position="popper"
            sideOffset={4}
          >
            <RadixSelect.ScrollUpButton className="flex items-center justify-center py-1 text-gray-400">
              <ChevronUp className="h-4 w-4" />
            </RadixSelect.ScrollUpButton>

            <RadixSelect.Viewport className="p-1">
              {options.map((opt) => (
                <RadixSelect.Item
                  key={opt.value}
                  value={opt.value}
                  disabled={opt.disabled}
                  className={cn(
                    'relative flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm',
                    'text-gray-700 outline-none',
                    'data-[highlighted]:bg-gray-100 data-[highlighted]:text-gray-900',
                    'data-[disabled]:pointer-events-none data-[disabled]:opacity-40',
                    'transition-colors'
                  )}
                >
                  <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator className="ml-auto">
                    <Check className="h-3.5 w-3.5 text-primary-400" />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>

            <RadixSelect.ScrollDownButton className="flex items-center justify-center py-1 text-gray-400">
              <ChevronDown className="h-4 w-4" />
            </RadixSelect.ScrollDownButton>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
      {hint && !error && (
        <p className="text-xs text-gray-500">{hint}</p>
      )}
    </div>
  )
}

export default Select
