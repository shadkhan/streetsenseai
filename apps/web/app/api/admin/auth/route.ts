import { NextResponse } from 'next/server'

export async function POST(req: Request): Promise<NextResponse> {
  const { username, password } = (await req.json()) as { username: string; password: string }

  const expectedUser = process.env.ADMIN_USERNAME ?? 'admin'
  const expectedPass = process.env.ADMIN_PASSWORD ?? ''
  const secret       = process.env.ADMIN_SESSION_SECRET ?? ''

  if (!expectedPass || !secret) {
    return NextResponse.json({ ok: false, error: 'Admin not configured — set ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SESSION_SECRET in .env.local' }, { status: 503 })
  }

  if (username === expectedUser && password === expectedPass) {
    const res = NextResponse.json({ ok: true })
    res.cookies.set('ss_admin_session', secret, {
      httpOnly: true,
      sameSite: 'strict',
      maxAge: 60 * 60 * 8,  // 8 hours
      path: '/',
      secure: process.env.NODE_ENV === 'production',
    })
    return res
  }

  return NextResponse.json({ ok: false, error: 'Invalid credentials' }, { status: 401 })
}
