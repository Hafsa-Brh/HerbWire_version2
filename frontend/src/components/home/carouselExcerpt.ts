export function presentationExcerpt(text: string, headline: string, target = 145) {
  const normalized = text.replace(/\s+/g, " ").trim()
  if (!normalized || normalized.toLocaleLowerCase() === headline.trim().toLocaleLowerCase()) return ""

  const firstSentence = normalized.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim()
  if (firstSentence && firstSentence.length >= 80 && firstSentence.length <= 150) return firstSentence
  if (normalized.length <= target) return normalized

  const shortened = normalized
    .slice(0, target + 1)
    .replace(/\s+\S*$/, "")
    .replace(/[,:;\-–—]+$/, "")
    .trim()
  return `${shortened}\u2026`
}