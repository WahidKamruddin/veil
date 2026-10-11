import { useMemo, useState } from 'react'
import { ArrowDown, ArrowCounterClockwise } from '@phosphor-icons/react'
import { redact } from '../lib/detect'

// Every value below is fake. AKIAIOSFODNN7EXAMPLE is AWS's published example key.
const SAMPLE = `Deploy keeps failing, can you look?
Ping me at dana.okafor@northwind.dev
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
Card on file: 4242 4242 4242 4242
Build 1234567812345678, commit 9fceb02d0ae598e95dc970b74767f19372d61af8`

export function Playground() {
  const [text, setText] = useState(SAMPLE)
  const { segments, count } = useMemo(() => redact(text), [text])

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-[0_24px_60px_-30px_rgba(0,0,0,0.25)]">
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <label htmlFor="prompt" className="text-sm font-medium">
          Your prompt
        </label>
        <button
          type="button"
          onClick={() => setText(SAMPLE)}
          disabled={text === SAMPLE}
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs text-muted transition hover:bg-tint hover:text-ink active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40"
        >
          <ArrowCounterClockwise size={14} weight="bold" />
          Reset
        </button>
      </div>
      <textarea
        id="prompt"
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        rows={6}
        className="block w-full resize-none bg-transparent px-5 py-4 font-mono text-[13px] leading-relaxed text-ink outline-none placeholder:text-muted focus-visible:bg-tint/60"
        placeholder="Paste anything with a key or an email in it"
      />
      <div className="flex items-center gap-3 border-y border-line bg-tint px-5 py-2.5 text-xs text-muted">
        <ArrowDown size={14} weight="bold" />
        <span>
          Through Veil:{' '}
          <span className="font-medium text-ink">
            {count === 0 ? 'nothing to redact' : `${count} ${count === 1 ? 'value' : 'values'} redacted`}
          </span>
        </span>
      </div>
      <div className="px-5 py-4">
        <p className="mb-2 text-sm font-medium">What the model sees</p>
        <pre aria-live="polite" className="min-h-[9.5rem] whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-muted">
          {segments.length === 0 ? (
            <span className="italic">Type above to see the sanitized request.</span>
          ) : (
            segments.map((s, i) =>
              s.kind ? (
                <span key={i} className="rounded-md bg-ink px-1 py-0.5 text-paper">
                  {s.text}
                </span>
              ) : (
                <span key={i}>{s.text}</span>
              ),
            )
          )}
        </pre>
      </div>
    </div>
  )
}
