/**
 * Next.js API Route Proxy to FastAPI Backend
 *
 * Forwards all requests from /api/* to the FastAPI backend at localhost:8123
 */

import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8123'

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path, 'GET')
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path, 'POST')
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path, 'PUT')
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path, 'DELETE')
}

export async function PATCH(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path, 'PATCH')
}

async function proxyRequest(request: NextRequest, path: string[], method: string) {
  try {
    // Build the backend URL
    const pathString = path.join('/')
    const searchParams = request.nextUrl.searchParams.toString()
    const backendUrl = `${BACKEND_URL}/${pathString}${searchParams ? `?${searchParams}` : ''}`

    console.log(`[API Proxy] ${method} ${backendUrl}`)

    // Get request body if present
    let body = null
    if (method !== 'GET' && method !== 'DELETE') {
      try {
        body = await request.json()
      } catch {
        // No body or not JSON
      }
    }

    // Forward request to backend
    const response = await fetch(backendUrl, {
      method,
      headers: {
        'Content-Type': 'application/json',
        // Forward relevant headers
        ...Object.fromEntries(
          Array.from(request.headers.entries()).filter(([key]) =>
            ['authorization', 'cookie'].includes(key.toLowerCase())
          )
        ),
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    // Get response data
    const data = await response.json().catch(() => null)

    // Return response with same status
    return NextResponse.json(data, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  } catch (error) {
    console.error('[API Proxy] Error:', error)
    return NextResponse.json(
      { error: 'Proxy error', message: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
