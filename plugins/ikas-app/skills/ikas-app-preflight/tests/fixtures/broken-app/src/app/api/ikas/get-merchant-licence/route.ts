import { getIkas } from '@/helpers/api-helpers';
import { withMerchant } from '@/lib/with-merchant';
import { NextResponse } from 'next/server';

export const GET = withMerchant(async (_request, { authToken }) => {
  const response = await getIkas(authToken).queries.getMerchantLicence();
  return NextResponse.json({ data: response.data?.getMerchantLicence ?? null });
});
