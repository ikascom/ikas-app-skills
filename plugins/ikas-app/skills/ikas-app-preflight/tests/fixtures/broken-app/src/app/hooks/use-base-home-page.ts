'use client';

import { AppBridgeHelper } from '@ikas/app-helpers';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { TokenHelpers } from '@/helpers/token-helpers';

/**
 * Custom hook for managing the base home page authentication and routing logic.
 * 
 * This hook handles the initial authentication flow for the application by:
 * - Checking for existing valid tokens in both iFrame and direct access contexts
 * - Managing OAuth authorization redirects for new users
 * - Routing users to appropriate pages based on their authentication status
 * - Handling both internal (iFrame within ikas dashboard) and external (direct browser) access scenarios
 * 
 * @returns An object containing the loading state
 */
export function useBaseHomePage() {
  // Track loading state during authentication flow
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    /**
     * Initializes the authentication and authorization flow.
     * 
     * This function orchestrates the entire authentication process:
     * 1. Closes any existing ikas AppBridge loader
     * 2. Attempts to retrieve existing token from iFrame context
     * 3. Routes to dashboard if valid token exists
     * 4. Handles OAuth flow initiation for external access
     * 5. Redirects to authorization page for missing tokens
     */
    const initializeAuthFlow = async () => {
      try {
        // Close any existing loader in the ikas AppBridge to prevent UI conflicts
        AppBridgeHelper.closeLoader();

        // Attempt to retrieve token from iFrame context (when app runs inside ikas dashboard)
        const existingToken = await TokenHelpers.getTokenForIframeApp();

        if (existingToken) {
          // Valid token found - user is already authenticated, proceed to main application
          router.push('/dashboard');
          return;
        }

        // No valid token found - need to handle authorization flow
        await handleAuthorizationFlow();

      } catch (error) {
        console.error('Error during base home page initialization:', error);
        
        // Fallback to authorization page on any unexpected errors
        router.push('/authorize-store');
      } finally {
        // Always reset loading state when initialization completes
        setIsLoading(false);
      }
    };

    /**
     * Handles the authorization flow when no valid token is present.
     * 
     * Determines the appropriate authorization path based on:
     * - Whether the app is running in an iFrame (internal) or standalone (external)
     * - Presence of store name in URL parameters for direct OAuth flow
     */
    const handleAuthorizationFlow = async () => {
      // Check if app is running outside of iFrame (direct browser access)
      if (window.self === window.top) {
        // External access - check for storeName parameter to initiate OAuth
        const urlParams = new URLSearchParams(window.location.search);
        const storeName = urlParams.get('storeName');

        if (storeName) {
          // Store name provided - redirect directly to OAuth authorization endpoint
          window.location.replace(`/api/oauth/authorize/ikas?storeName=${storeName}`);
          return;
        }
      }

      // Either running in iFrame or no storeName provided - redirect to manual authorization page
      router.push('/authorize-store');
    };

    // Prevent multiple simultaneous initialization attempts
    if (isLoading) {
      return;
    }

    // Set loading state and begin initialization
    setIsLoading(true);
    initializeAuthFlow();

    // No cleanup required - all operations are async and self-contained
    return () => {};
    
    // Dependencies intentionally minimal - only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Return loading state for consuming components
  return { isLoading };
}
