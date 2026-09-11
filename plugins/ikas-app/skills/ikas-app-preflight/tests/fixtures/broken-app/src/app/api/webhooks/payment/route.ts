import { prisma } from '@/lib/prisma';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const webhook = await request.json();
  const data = JSON.parse(webhook.data);
  const payment = data.merchantAppPayment;
  await prisma.subscription.upsert({
    where: { merchantId: webhook.merchantId },
    create: { merchantId: webhook.merchantId, plan: payment.storeAppListingSubscriptionKey },
    update: { plan: payment.storeAppListingSubscriptionKey },
  });
  return NextResponse.json({ ok: true });
}
