import { NextRequest, NextResponse } from 'next/server';
import { getUserFromRequest } from '@/lib/auth-helpers';
import { AuthTokenManager } from '@/models/auth-token/manager';
import { AuthToken } from '@/models/auth-token';

type Handler = (request: NextRequest, ctx: { authToken: AuthToken; merchantId: string }) => Promise<NextResponse>;

export function withMerchant(handler: Handler) {
  return async (request: NextRequest) => {
    const user = getUserFromRequest(request);
    if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    const authToken = await AuthTokenManager.get(user.authorizedAppId);
    if (!authToken) return NextResponse.json({ error: { statusCode: 404, message: 'Auth token not found' } }, { status: 404 });
    return handler(request, { authToken, merchantId: user.merchantId });
  };
}
