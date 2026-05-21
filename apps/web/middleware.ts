import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

const COOKIE_NAME = 'ss_admin_session'

const isAuthorityRoute = createRouteMatcher(['/authority(.*)'])

export default clerkMiddleware(async (auth, req) => {
  // /authority/* — Clerk-authenticated routes (DT-004)
  if (isAuthorityRoute(req)) {
    await auth.protect()
    return
  }

  // /admin/* — legacy cookie-based session guard
  const { pathname } = req.nextUrl
  if (pathname.startsWith('/admin') && pathname !== '/admin/login' && !pathname.startsWith('/api/admin/auth')) {
    const session = req.cookies.get(COOKIE_NAME)?.value
    const secret = process.env.ADMIN_SESSION_SECRET ?? ''
    if (!secret || session !== secret) {
      const loginUrl = new URL('/admin/login', req.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
