// Browser port of a subset of backend/app/detect.py, used only for the live demo.
// Same idea: collect spans from every rule, keep the highest priority then longest, replace in one pass.

type Rule = {
  kind: string
  prio: number
  pattern: RegExp
  group?: number
  validate?: (value: string) => boolean
}

export type Segment = { text: string; kind?: string }

const luhn = (digits: string) => {
  let total = 0
  ;[...digits].reverse().forEach((ch, i) => {
    let d = Number(ch)
    if (i % 2 === 1) {
      d *= 2
      if (d > 9) d -= 9
    }
    total += d
  })
  return total % 10 === 0
}

const entropy = (s: string) => {
  const counts = new Map<string, number>()
  for (const ch of s) counts.set(ch, (counts.get(ch) ?? 0) + 1)
  let h = 0
  for (const c of counts.values()) h -= (c / s.length) * Math.log2(c / s.length)
  return h
}

const validCard = (v: string) => {
  const digits = v.replace(/[ -]/g, '')
  return digits.length >= 13 && digits.length <= 19 && luhn(digits)
}

const validSecret = (v: string) =>
  !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v) &&
  !/^[0-9a-f]{32,64}$/i.test(v) &&
  entropy(v) > 3.5

const RULES: Rule[] = [
  { kind: 'PRIVATE_KEY', prio: 100, pattern: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----/g },
  { kind: 'ANTHROPIC_KEY', prio: 95, pattern: /sk-ant-[A-Za-z0-9_-]{20,}/g },
  { kind: 'OPENAI_KEY', prio: 90, pattern: /sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}/g },
  { kind: 'GITHUB_TOKEN', prio: 90, pattern: /gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}/g },
  { kind: 'AWS_KEY', prio: 90, pattern: /\b(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}\b/g },
  { kind: 'STRIPE_KEY', prio: 90, pattern: /\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|\bwhsec_[A-Za-z0-9]{16,}/g },
  {
    kind: 'OTHER_TOKEN',
    prio: 85,
    pattern: /xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|[A-Za-z][A-Za-z0-9+.-]*:\/\/[^\s:/@]+:[^\s/@]+@[^\s/]+/g,
  },
  { kind: 'SSN', prio: 80, pattern: /\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b/g },
  { kind: 'CREDIT_CARD', prio: 80, pattern: /\b(?:\d[ -]?){12,18}\d\b/g, validate: validCard },
  { kind: 'EMAIL', prio: 70, pattern: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g },
  {
    kind: 'SECRET',
    prio: 60,
    pattern: /(?:key|token|secret|passw\w*|bearer)[\w\s"']{0,20}[:=]\s*["']?([A-Za-z0-9_\-+/=.~]{16,})/gi,
    group: 1,
    validate: validSecret,
  },
]

type Span = { start: number; end: number; kind: string; prio: number; value: string }

export function redact(text: string): { segments: Segment[]; count: number } {
  const spans: Span[] = []
  for (const rule of RULES) {
    for (const m of text.matchAll(rule.pattern)) {
      const value = m[rule.group ?? 0]
      if (!value || (rule.validate && !rule.validate(value))) continue
      // The captured value always ends the match, so its start is measured back from the end.
      const start = m.index + m[0].length - value.length
      spans.push({ start, end: start + value.length, kind: rule.kind, prio: rule.prio, value })
    }
  }

  const accepted: Span[] = []
  for (const s of spans.sort((a, b) => b.prio - a.prio || b.end - b.start - (a.end - a.start) || a.start - b.start)) {
    if (accepted.every((a) => s.end <= a.start || s.start >= a.end)) accepted.push(s)
  }
  accepted.sort((a, b) => a.start - b.start)

  // Deterministic placeholders: the same value always gets the same token.
  const counters = new Map<string, number>()
  const seen = new Map<string, string>()
  const segments: Segment[] = []
  let pos = 0
  for (const s of accepted) {
    if (s.start > pos) segments.push({ text: text.slice(pos, s.start) })
    const key = `${s.kind}:${s.kind === 'EMAIL' ? s.value.toLowerCase() : s.value}`
    let token = seen.get(key)
    if (!token) {
      const n = (counters.get(s.kind) ?? 0) + 1
      counters.set(s.kind, n)
      token = `[${s.kind}_${n}]`
      seen.set(key, token)
    }
    segments.push({ text: token, kind: s.kind })
    pos = s.end
  }
  if (pos < text.length) segments.push({ text: text.slice(pos) })
  return { segments, count: accepted.length }
}
