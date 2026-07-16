export function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const secs = Math.floor(diff / 1000)
  const mins = Math.floor(secs / 60)
  const hrs = Math.floor(mins / 60)
  const days = Math.floor(hrs / 24)
  if (days > 30) return d.toLocaleDateString()
  if (days > 0) return days + 'd ago'
  if (hrs > 0) return hrs + 'h ago'
  if (mins > 0) return mins + 'm ago'
  return 'just now'
}
