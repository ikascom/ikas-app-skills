'use client';

import { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    window.location.href = 'https://app.example-crm.com/login?next=/integrations/ikas';
  }, []);
  return null;
}
