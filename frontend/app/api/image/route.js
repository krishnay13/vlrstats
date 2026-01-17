import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const IMAGES_DIR = path.join(__dirname, '..', '..', '..', 'public', 'images')

const CONTENT_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
}

export async function GET(request) {
  const { searchParams } = new URL(request.url)
  const name = searchParams.get('name')
  if (!name) {
    return new Response('Missing image name', { status: 400 })
  }

  const safeName = path.basename(name)
  if (safeName !== name) {
    return new Response('Invalid image name', { status: 400 })
  }

  const ext = path.extname(safeName).toLowerCase()
  const contentType = CONTENT_TYPES[ext]
  if (!contentType) {
    return new Response('Unsupported image type', { status: 400 })
  }

  const imagePath = path.join(IMAGES_DIR, safeName)
  try {
    const data = await fs.readFile(imagePath)
    return new Response(data, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400',
      },
    })
  } catch (error) {
    return new Response('Image not found', { status: 404 })
  }
}
