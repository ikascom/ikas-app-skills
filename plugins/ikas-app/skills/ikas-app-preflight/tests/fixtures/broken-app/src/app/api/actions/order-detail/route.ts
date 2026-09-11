import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const data = JSON.parse(body.data);
  await prisma.actionRun.create({ data: { id: data.actionRunId, merchantId: body.merchantId, orderIds: data.idList } });
  return NextResponse.json({ success: true });
}
