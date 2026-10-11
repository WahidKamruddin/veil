import { useState } from 'react'
import { Check, Copy } from '@phosphor-icons/react'
import { Reveal } from './ui'

const steps = [
  { label: 'Install', cmd: "cd backend && pip install -e '.[dev]'" },
  { label: 'Start', cmd: 'uvicorn app.main:app --port 8080' },
  { label: 'Point', cmd: 'ANTHROPIC_BASE_URL=http://localhost:8080 claude' },
]

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setState('copied')
    } catch {
      setState('failed')
    }
    setTimeout(() => setState('idle'), 1600)
  }
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={`Copy: ${text}`}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-paper/20 px-3 py-1.5 text-xs text-paper transition hover:border-paper/50 active:scale-[0.98]"
    >
      {state === 'copied' ? <Check size={14} weight="bold" /> : <Copy size={14} />}
      {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : 'Copy'}
    </button>
  )
}

export function Install() {
  return (
    <section id="install" className="mx-auto max-w-4xl scroll-mt-16 px-4 py-24 md:px-8 md:py-32">
      <Reveal>
        <h2 className="text-3xl font-semibold tracking-tight md:text-5xl">Running in under a minute.</h2>
        <p className="mt-5 max-w-[56ch] text-lg leading-relaxed text-muted">
          Three commands. For OpenAI clients, set <code className="font-mono text-ink">OPENAI_BASE_URL</code> instead.
        </p>
      </Reveal>
      <ol className="mt-12 space-y-4">
        {steps.map(({ label, cmd }, i) => (
          <Reveal key={label} delay={i * 0.06}>
            <li className="grid grid-cols-1 items-center gap-3 md:grid-cols-[6rem_1fr]">
              <span className="text-sm font-medium text-muted">{label}</span>
              <div className="flex items-center justify-between gap-4 rounded-2xl bg-ink px-5 py-4 text-paper">
                <code className="overflow-x-auto whitespace-nowrap font-mono text-sm">
                  <span className="select-none opacity-50">$ </span>
                  {cmd}
                </code>
                <CopyButton text={cmd} />
              </div>
            </li>
          </Reveal>
        ))}
      </ol>
    </section>
  )
}
