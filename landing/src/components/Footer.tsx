import { Mark } from './ui'

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 py-12 text-sm text-muted md:grid-cols-[1fr_auto] md:px-8">
        <div>
          <p className="flex items-center gap-2.5 text-base font-semibold text-ink">
            <Mark />
            Veil
          </p>
          <p className="mt-3 max-w-[60ch] leading-relaxed">
            Not covered yet: images and files, Realtime, embeddings, Bedrock and Vertex, and names or addresses.
          </p>
        </div>
        <a href="#top" className="self-end transition-colors hover:text-ink">
          Back to top
        </a>
      </div>
    </footer>
  )
}
