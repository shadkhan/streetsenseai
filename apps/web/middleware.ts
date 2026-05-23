import { NextRequest, NextResponse } from 'next/server'

const COOKIE_NAME = 'ss_admin_session'

// Clerk keys are not configured for the demo deployment.
// /authority/* routes are accessible without auth until Clerk is wired up.
// See DT-004 — re-enable clerkMiddleware when CLERK_SECRET_KEY is set in Vercel.
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  if (
    pathname.startsWith('/admin') &&
    pathname !== '/admin/login' &&
    !pathname.startsWith('/api/admin/auth')
  ) {
    const session = req.cookies.get(COOKIE_NAME)?.value
    const secret = process.env.ADMIN_SESSION_SECRET ?? ''
    if (!secret || session !== secret) {
      const loginUrl = new URL('/admin/login', req.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
