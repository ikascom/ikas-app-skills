'use client';

import { useSearchParams } from 'next/navigation';

export default function OrderListActionPage() {
  const params = useSearchParams();
  const idList = (params.get('idList') || '').split(',');
  const actionRunId = params.get('actionRunId');
  return <div>Seçili sipariş: {idList.length} ({actionRunId})</div>;
}
