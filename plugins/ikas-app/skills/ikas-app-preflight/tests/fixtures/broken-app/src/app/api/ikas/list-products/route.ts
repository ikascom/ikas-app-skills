import { getIkas } from '@/helpers/api-helpers';
import { AuthTokenManager } from '@/models/auth-token/manager';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const authorizedAppId = request.nextUrl.searchParams.get('authorizedAppId')!;
  const authToken = await AuthTokenManager.get(authorizedAppId);
  if (!authToken) return NextResponse.json({ error: 'not found' }, { status: 404 });
  const products = await getIkas(authToken).queries.listProduct({ pagination: { limit: 10 } });
  return NextResponse.json({ data: products.data });
}

// v1-only mutation name on a v2 app (§5.3): fails with GRAPHQL_VALIDATION_FAILED at runtime
export async function POST(req: NextRequest) {
  const authToken = await AuthTokenManager.get(req.nextUrl.searchParams.get('authorizedAppId')!);
  if (!authToken) return NextResponse.json({ error: 'not found' }, { status: 404 });
  const res = await getIkas(authToken).mutations.saveProduct({ input: { name: 'x' } } as never);
  return NextResponse.json(res);
}
