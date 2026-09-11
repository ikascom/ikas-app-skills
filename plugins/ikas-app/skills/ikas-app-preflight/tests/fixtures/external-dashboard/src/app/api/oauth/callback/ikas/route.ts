import { config } from '@/globals/config';
import { getSession } from '@/lib/session';
import { OAuthAPI } from '@ikas/admin-api-client';
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

const callbackSchema = z.object({
  code: z.string().min(1),
  state: z.string().min(1),
  storeName: z.string().min(1),
});

export async function GET(request: NextRequest) {
  const parsed = callbackSchema.safeParse(Object.fromEntries(request.nextUrl.searchParams));
  if (!parsed.success) {
    return NextResponse.redirect('https://app.example-crm.com/login?next=%2Fintegrations%2Fikas%3Ferror%3Dmissing_code');
  }
  const { code, state, storeName } = parsed.data;
  const session = await getSession();
  if (!session.state || session.state !== state || !session.crmUserId) {
    return new NextResponse('This install link has expired. Start again from ikas.', { status: 400 });
  }
  const token = await OAuthAPI.getTokenWithAuthorizationCode(
    { code, client_id: config.oauth.clientId!, client_secret: config.oauth.clientSecret!, redirect_uri: config.oauth.redirectUri },
    { storeName },
  );
  if (!token.data) return NextResponse.json({ error: 'Callback failed' }, { status: 500 });
  // R3: the token is parked on the browser session; the CRM tenant is linked later by hand from the CRM settings page
  session.accessToken = token.data.access_token;
  session.refreshToken = token.data.refresh_token;
  await session.save();
  return NextResponse.redirect('https://app.example-crm.com/integrations/ikas/connect');
}
