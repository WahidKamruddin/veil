import { motion } from 'motion/react'
import type { ReactNode } from 'react'

// Shape rule for the whole page: interactive elements are full pills, containers are rounded-2xl.

export function Mark({ className = '' }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`inline-block size-5 rounded-full border-2 border-ink ${className}`}
      style={{ background: 'linear-gradient(90deg, transparent 50%, var(--ink) 50%)' }}
    />
  )
}

export function Button({ href, children, variant = 'primary' }: { href: string; children: ReactNode; variant?: 'primary' | 'ghost' }) {
  const styles =
    variant === 'primary'
      ? 'bg-ink text-paper hover:opacity-85'
      : 'border border-line text-ink hover:border-ink'
  return (
    <a
      href={href}
      className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-medium transition-[opacity,border-color,transform] duration-200 active:scale-[0.98] ${styles}`}
    >
      {children}
    </a>
  )
}

export function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.25 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}

export function Placeholder({ children, inverted = false }: { children: ReactNode; inverted?: boolean }) {
  return (
    <span
      className={`rounded-md px-1.5 py-0.5 font-mono text-[0.85em] [box-decoration-break:clone] ${
        inverted ? 'bg-paper text-ink' : 'bg-ink text-paper'
      }`}
    >
      {children}
    </span>
  )
}
