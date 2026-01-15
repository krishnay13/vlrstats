import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const IMAGES_DIR = path.join(__dirname, '..', '..', '..', 'images')

const EVENT_LOGOS = {
  AMERICAS: 'americaslogo.png',
  EMEA: 'emealogo.png',
  APAC: 'apaclogo.png',
  CHINA: 'chinalogo.png',
  MASTERS: 'masterslogo.png',
  CHAMPIONS: 'championslogo.png',
}

let logoIndex = null
const SMALL_MAX_SIZE = 120

function stripDiacritics(value) {
  return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
}

function normalizeKey(value) {
  if (!value) return ''
  let normalized = stripDiacritics(String(value))
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
  normalized = normalized.replace(/esports$/i, '')
  return normalized
}

function deriveNameAndSize(filename) {
  const withoutExt = filename.replace(/\.[^.]+$/, '')
  const sizeMatch = withoutExt.match(/^(\d+)px-(.+)$/i)
  const size = sizeMatch ? Number(sizeMatch[1]) : 0
  let namePart = sizeMatch ? sizeMatch[2] : withoutExt

  namePart = namePart.replace(/_(allmode|darkmode|lightmode|full|full_darkmode|full_lightmode)$/i, '')
  namePart = namePart.replace(/[_-]\d{4}/g, '')
  namePart = namePart.replace(/\besports\b/i, '')
  namePart = namePart.replace(/_/g, ' ')
  namePart = namePart.trim()

  return { namePart, size }
}

const LOGO_ALIASES = {
  furia: ['furiaesports'],
  futbolist: ['fut', 'futbolistic', 'futbolistick'],
  teamheretics: ['heretics'],
  nongshimredforce: ['nsredforce', 'nongshim'],
  geng: ['gengesports', 'gengg', 'genge', 'gengesport'],
  xilai: ['xlg', 'xilaigaming', 'xlgchina'],
  jdgaming: ['jdg', 'jdgaming', 'jdgteam'],
}

const TEAM_LOGO_OVERRIDES = {
  nongshimredforce: {
    small: '37px-NS_Redforce_allmode.png',
  },
  xilai: {
    small: '69px-XLG_China_2024_allmode.png',
  },
}

function buildLogoIndex() {
  if (logoIndex) return logoIndex
  const index = new Map()
  try {
    const entries = fs.readdirSync(IMAGES_DIR, { withFileTypes: true })
    for (const entry of entries) {
      if (!entry.isFile()) continue
      const filename = entry.name
      const ext = path.extname(filename).toLowerCase()
      if (!['.png', '.jpg', '.jpeg', '.webp', '.svg'].includes(ext)) continue

      const { namePart, size } = deriveNameAndSize(filename)
      if (!namePart) continue
      const key = normalizeKey(namePart)
      const existing = index.get(key) || []
      index.set(key, [...existing, { filename, size }])
    }
    for (const [canonical, aliases] of Object.entries(LOGO_ALIASES)) {
      const keys = [canonical, ...aliases]
      const existingEntry = keys.map((key) => index.get(key)).find((entry) => entry && entry.length > 0)
      if (!existingEntry) continue
      keys.forEach((key) => {
        if (!index.has(key)) {
          index.set(key, existingEntry)
        }
      })
    }
  } catch (error) {
    console.error('Failed to build logo index:', error)
  }
  logoIndex = index
  return index
}

function selectLogoEntry(entries, sizePreference) {
  if (!entries || entries.length === 0) return null
  const sorted = [...entries].sort((a, b) => a.size - b.size)
  if (sizePreference === 'small') {
    const small = sorted.filter((entry) => entry.size > 0 && entry.size <= SMALL_MAX_SIZE)
    return (small.length > 0 ? small[small.length - 1] : sorted[sorted.length - 1])
  }
  if (sizePreference === 'large') {
    return sorted[sorted.length - 1]
  }
  return sorted[sorted.length - 1]
}

export function getTeamLogoFile(teamName, sizePreference = 'large') {
  if (!teamName) return null
  const index = buildLogoIndex()
  const key = normalizeKey(teamName)
  const override = TEAM_LOGO_OVERRIDES[key]
  if (override) {
    const forced = override[sizePreference] || override.default || override.small
    if (forced) return forced
  }
  if (index.has(key)) {
    const entry = selectLogoEntry(index.get(key), sizePreference)
    return entry ? entry.filename : null
  }
  return null
}

export function getTeamLogoUrl(teamName, sizePreference = 'large') {
  const file = getTeamLogoFile(teamName, sizePreference)
  return file ? `/api/image?name=${encodeURIComponent(file)}` : null
}

export function getEventLogoUrl({ region, tournament }) {
  const tournamentLower = (tournament || '').toLowerCase()
  if (tournamentLower.includes('masters')) {
    return `/api/image?name=${encodeURIComponent(EVENT_LOGOS.MASTERS)}`
  }
  if (tournamentLower.includes('champions') && !tournamentLower.includes('champions tour')) {
    return `/api/image?name=${encodeURIComponent(EVENT_LOGOS.CHAMPIONS)}`
  }
  if (region && EVENT_LOGOS[region]) {
    return `/api/image?name=${encodeURIComponent(EVENT_LOGOS[region])}`
  }
  return null
}
