'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Loading from '@/components/Loading';
import { TokenHelpers } from '@/helpers/token-helpers';

/**
 * CallbackContent
 * - Handles the OAuth callback logic.
 * - Extracts query parameters from the URL.
 * - Sets the token using TokenHelpers and redirects as needed.
 * - Shows a loading spinner while processing.
 */
function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Immediately-invoked async function to handle token setting and redirect
    (async () => {
      // Convert searchParams to URLSearchParams for compatibility
      const params = new URLSearchParams(searchParams.toString());
      // Log params for debugging purposes
      console.log('OAuth callback params:', params.toString());
      // Set token and handle redirect logic
      await TokenHelpers.setToken(router, params);
    })();
  }, [router, searchParams]);

  // Show loading indicator while processing callback
  return <Loading />;
}

/**
 * CallbackPage
 * - Wraps CallbackContent in Suspense for async handling.
 */
export default function CallbackPage() {
  return (
    <Suspense>
      <CallbackContent />
    </Suspense>
  );
}
