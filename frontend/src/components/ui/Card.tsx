import type { HTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/cn'

const cardVariants = cva(
  'rounded-2xl transition-all duration-200',
  {
    variants: {
      variant: {
        default: [
          'bg-white border border-gray-200 shadow-card',
        ],
        elevated: [
          'bg-white shadow-panel border border-gray-100',
          'hover:border-gray-200 hover:shadow-xl transition-shadow',
        ],
        bordered: [
          'bg-gray-50 border border-gray-200 shadow-sm',
          'hover:border-gray-300',
        ],
        gradient: [
          'bg-gradient-to-br from-white to-gray-50',
          'border border-gray-200 shadow-card',
        ],
        ghost: [
          'bg-transparent border border-gray-200/50',
        ],
      },
      padding: {
        none: '',
        sm: 'p-4',
        md: 'p-6',
        lg: 'p-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
    },
  }
)

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  hoverable?: boolean
}

export function Card({ className, variant, padding, hoverable, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        cardVariants({ variant, padding, className }),
        hoverable && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-panel'
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('mb-4 flex items-center justify-between', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-base font-semibold text-gray-900', className)} {...props}>
      {children}
    </h3>
  )
}

export function CardDescription({ className, children, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-sm text-gray-500', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('', className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('mt-4 flex items-center border-t border-gray-200 pt-4', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export default Card
