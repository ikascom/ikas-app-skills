import { AuthTokenManager } from '@/models/auth-token/manager';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const webhook = await request.json();
    if (webhook.scope === 'store/app/deleted') {
      const authToken = await AuthTokenManager.get(webhook.authorizedAppId);
      if (!authToken) return NextResponse.json({ ok: true, skipped: true });
      await AuthTokenManager.delete(webhook.authorizedAppId);
    }
    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error('webhook error', error);
    return NextResponse.json({ ok: true });
  }
}
