import { motion } from 'motion/react'
import { Button } from './ui'
import { Playground } from './Playground'

const enter = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] as const },
})

export function Hero() {
  return (
    <section id="top" className="mx-auto grid min-h-[calc(100dvh-4rem)] max-w-7xl grid-cols-1 items-center gap-12 px-4 py-16 md:px-8 lg:grid-cols-[1fr_1.05fr] lg:gap-16 lg:py-20">
      <div className="max-w-xl">
        <motion.h1 {...enter(0)} className="text-4xl font-semibold leading-[1.05] tracking-tighter md:text-5xl lg:text-6xl">
          The model never sees your secrets.
        </motion.h1>
        <motion.p {...enter(0.08)} className="mt-6 max-w-[42ch] text-lg leading-relaxed text-muted">
          A local proxy that strips keys and personal data from every prompt, then puts them back in the reply.
        </motion.p>
        <motion.div {...enter(0.16)} className="mt-9 flex flex-wrap gap-3">
          <Button href="#install">Get started</Button>
          <Button href="#how" variant="ghost">
            How it works
          </Button>
        </motion.div>
      </div>
      <motion.div {...enter(0.24)}>
        <Playground />
      </motion.div>
    </section>
  )
}
