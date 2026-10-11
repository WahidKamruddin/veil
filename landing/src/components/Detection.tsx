import { Fingerprint, Key, LockKeyOpen, Prohibit } from '@phosphor-icons/react'
import { Reveal } from './ui'

const tokens = ['Anthropic', 'OpenAI', 'GitHub', 'AWS', 'Stripe', 'Slack', 'Google', 'JWT', 'Private keys', 'URL credentials']
const personal = ['Emails', 'Card numbers', 'SSNs', 'Phone numbers']
const untouched = ['UUIDs', 'Git SHAs', 'Random 16-digit IDs', 'Plain English']

function Chips({ items, inverted = false }: { items: string[]; inverted?: boolean }) {
  return (
    <ul className="mt-6 flex flex-wrap gap-2">
      {items.map((t) => (
        <li
          key={t}
          className={`rounded-full border px-3 py-1 text-sm ${inverted ? 'border-paper/25 text-paper' : 'border-line bg-surface'}`}
        >
          {t}
        </li>
      ))}
    </ul>
  )
}

export function Detection() {
  return (
    <section id="detection" className="mx-auto max-w-7xl scroll-mt-16 px-4 py-24 md:px-8 md:py-32">
      <Reveal className="max-w-2xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-5xl">Knows what a secret looks like.</h2>
        <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted">
          Pattern rules, checksums and entropy scoring catch real secrets while leaving ordinary IDs alone.
        </p>
      </Reveal>

      <div className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-6">
        <Reveal className="md:col-span-4 md:row-span-2">
          <article className="flex h-full flex-col justify-between rounded-2xl bg-ink p-8 text-paper md:p-10">
            <div>
              <Key size={32} />
              <h3 className="mt-8 text-2xl font-semibold tracking-tight md:text-3xl">API keys and tokens</h3>
              <p className="mt-3 max-w-[46ch] leading-relaxed opacity-70">
                Provider keys are matched by their exact formats. Secret values are never restored into plain text.
              </p>
            </div>
            <Chips items={tokens} inverted />
          </article>
        </Reveal>

        <Reveal delay={0.06} className="md:col-span-2">
          <article className="h-full rounded-2xl border border-line bg-surface p-8">
            <Fingerprint size={28} />
            <h3 className="mt-6 text-xl font-semibold">Personal data</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">Card numbers must pass a Luhn check. Phone matching is optional.</p>
            <Chips items={personal} />
          </article>
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-2">
          <article
            className="h-full rounded-2xl border border-line p-8"
            style={{ backgroundImage: 'radial-gradient(var(--line) 1px, transparent 1px)', backgroundSize: '14px 14px' }}
          >
            <LockKeyOpen size={28} />
            <h3 className="mt-6 text-xl font-semibold">High-entropy secrets</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Anything assigned to a key, token, secret or password that looks random enough.
            </p>
          </article>
        </Reveal>

        <Reveal delay={0.06} className="md:col-span-6">
          <article
            className="grid grid-cols-1 items-center gap-6 rounded-2xl border border-line p-8 md:grid-cols-[auto_1fr_auto] md:gap-10"
            style={{ backgroundImage: 'repeating-linear-gradient(135deg, var(--tint) 0 10px, transparent 10px 20px)' }}
          >
            <Prohibit size={28} />
            <div>
              <h3 className="text-xl font-semibold">Left alone on purpose</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">False positives break prompts, so look-alikes pass straight through.</p>
            </div>
            <ul className="flex flex-wrap gap-2">
              {untouched.map((t) => (
                <li key={t} className="rounded-full border border-line bg-surface px-3 py-1 text-sm text-muted line-through decoration-muted/60">
                  {t}
                </li>
              ))}
            </ul>
          </article>
        </Reveal>
      </div>
    </section>
  )
}
