import { motion } from 'motion/react'
import { Cloud, ShieldCheck, TerminalWindow } from '@phosphor-icons/react'
import { Placeholder, Reveal } from './ui'

const hops = [
  { icon: TerminalWindow, title: 'Your client', body: 'Claude Code, an SDK app, or an agent.' },
  { icon: ShieldCheck, title: 'Veil on localhost:8080', body: 'Swaps secrets for placeholders. Holds the originals in memory.' },
  { icon: Cloud, title: 'Model API', body: 'Anthropic or OpenAI. Only ever sees placeholders.' },
]

// The upstream splits a placeholder across five separate stream events. Veil still restores it cleanly.
const chunks = ['Sent the invite to ', '[', 'EM', 'AIL', '_1', ']', ' just now.']

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-7xl scroll-mt-16 px-4 py-24 md:px-8 md:py-32">
      <Reveal className="max-w-2xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-5xl">Sits between your client and the API.</h2>
        <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted">
          Point your client at localhost. No code changes. Veil redacts on the way out and restores on the way back, even mid-stream.
        </p>
      </Reveal>

      <ol className="mt-16 grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-0">
        {hops.map(({ icon: Icon, title, body }, i) => (
          <Reveal key={title} delay={i * 0.08} className="relative">
            <li className={`h-full p-6 md:p-8 ${i === 1 ? 'rounded-2xl bg-ink text-paper' : 'rounded-2xl border border-line md:border-0'}`}>
              <Icon size={28} weight="regular" />
              <h3 className="mt-6 text-lg font-medium">{title}</h3>
              <p className={`mt-2 text-sm leading-relaxed ${i === 1 ? 'opacity-70' : 'text-muted'}`}>{body}</p>
            </li>
          </Reveal>
        ))}
      </ol>

      <Reveal className="mt-20 grid grid-cols-1 gap-10 rounded-2xl border border-line bg-surface p-6 md:p-10 lg:grid-cols-[1fr_1.4fr] lg:items-center">
        <div>
          <h3 className="text-2xl font-semibold tracking-tight">Placeholders survive any chunk split.</h3>
          <p className="mt-3 max-w-[48ch] leading-relaxed text-muted">
            Streams arrive in arbitrary pieces. Veil holds back only a possible partial token, so you never see a stray bracket.
          </p>
        </div>
        <div className="space-y-6">
          <div>
            <p className="mb-3 text-sm text-muted">Model streams</p>
            <motion.div
              className="flex flex-wrap gap-1.5 font-mono text-sm"
              initial="hidden"
              whileInView="shown"
              viewport={{ once: true, amount: 0.6 }}
              variants={{ shown: { transition: { staggerChildren: 0.18 } } }}
            >
              {chunks.map((c, i) => (
                <motion.span
                  key={i}
                  variants={{ hidden: { opacity: 0, y: 8 }, shown: { opacity: 1, y: 0 } }}
                  transition={{ type: 'spring', stiffness: 100, damping: 20 }}
                  className="whitespace-pre rounded-md border border-line bg-tint px-2 py-1"
                >
                  {c}
                </motion.span>
              ))}
            </motion.div>
          </div>
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ delay: chunks.length * 0.18 + 0.3, duration: 0.5 }}
          >
            <p className="mb-3 text-sm text-muted">You receive</p>
            <p className="font-mono text-sm">
              Sent the invite to <span className="border-b-2 border-ink font-medium">dana.okafor@northwind.dev</span> just now.
            </p>
          </motion.div>
          <p className="text-sm text-muted">
            The model wrote <Placeholder>[EMAIL_1]</Placeholder>. It never learned the address.
          </p>
        </div>
      </Reveal>
    </section>
  )
}
