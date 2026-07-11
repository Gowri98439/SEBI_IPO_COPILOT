import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

const buttonVariants = cva(
  // Base
  'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:pointer-events-none disabled:opacity-50 select-none',
  {
    variants: {
      variant: {
        primary: [
          'bg-gray-900 text-white shadow-sm',
          'hover:bg-gray-800 hover:-translate-y-0.5 hover:shadow',
          'active:translate-y-0 active:shadow-none',
        ],
        secondary: [
          'bg-white border border-gray-200 text-gray-700 shadow-sm',
          'hover:bg-gray-50 hover:text-gray-900',
          'active:scale-95',
        ],
        outline: [
          'border border-gray-200 bg-transparent text-gray-600',
          'hover:bg-gray-50 hover:text-gray-900',
          'active:scale-95',
        ],
        ghost: [
          'bg-transparent text-gray-500',
          'hover:bg-gray-100 hover:text-gray-900',
          'active:scale-95',
        ],
        danger: [
          'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-md',
          'hover:from-red-500 hover:to-rose-500 hover:shadow-lg hover:-translate-y-0.5',
          'active:translate-y-0',
        ],
        success: [
          'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md',
          'hover:from-emerald-500 hover:to-teal-500 hover:shadow-lg hover:-translate-y-0.5',
          'active:translate-y-0',
        ],
      },
      size: {
        sm: 'h-8 px-3 text-xs rounded-lg',
        md: 'h-10 px-4 text-sm',
        lg: 'h-11 px-6 text-base',
        xl: 'h-13 px-8 text-base',
        icon: 'h-9 w-9 p-0',
        'icon-sm': 'h-7 w-7 p-0 rounded-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, leftIcon, rightIcon, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={disabled ?? loading}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button, buttonVariants }
export default Button
