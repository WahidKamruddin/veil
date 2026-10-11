import { ThemeToggle } from './ThemeToggle'
import { Button, Mark } from './ui'

const links = [
  { href: '#how', label: 'How it works' },
  { href: '#detection', label: 'Detection' },
  { href: '#security', label: 'Security' },
]

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper/85 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-8">
        <a href="#top" className="flex items-center gap-2.5 text-lg font-semibold tracking-tight">
          <Mark />
          Veil
        </a>
        <div className="hidden items-center gap-8 text-sm text-muted md:flex">
          {links.map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button href="#install">Get started</Button>
        </div>
      </nav>
    </header>
  )
}
