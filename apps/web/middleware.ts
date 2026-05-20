import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const COOKIE_NAME = 'ss_admin_session'

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl

  // Allow login page and its API route through
  if (pathname === '/admin/login' || pathname.startsWith('/api/admin/auth')) {
    return NextResponse.next()
  }

  if (pathname.startsWith('/admin')) {
    const session = request.cookies.get(COOKIE_NAME)?.value
    const secret = process.env.ADMIN_SESSION_SECRET ?? ''

    if (!secret || session !== secret) {
      const loginUrl = new URL('/admin/login', request.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/:path*', '/api/admin/:path*'],
}
