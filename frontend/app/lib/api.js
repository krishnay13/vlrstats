export async function fetchJson(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options })
  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const text = await res.text()
      if (text) message = text
    } catch (error) {
      // Ignore parsing errors
    }
    throw new Error(message)
  }
  return res.json()
}
