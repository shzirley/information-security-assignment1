'use client';

import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export const buttonVariants = cva('button', {
  variants: {
    variant: { default: 'button-primary', secondary: 'button-secondary', outline: 'button-secondary', ghost: 'button-ghost', destructive: 'button-danger' },
    size: { default: '', lg: 'button-lg', sm: 'button-sm' },
  }, defaultVariants: { variant: 'default', size: 'default' },
});

export function Button({ asChild, className, variant, size, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : 'button';
  return <Component {...(!asChild ? { type: 'button' as const } : {})} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
