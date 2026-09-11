import { AppBridgeHelper } from '@ikas/app-helpers';
import { useRouter } from 'next/navigation';
import crypto from 'crypto';

/** Key used for storing tokens in session storage */
const TOKEN_KEY = 'token';

/**
 * Utility class for managing authentication tokens in ikas applications.
 * 
 * This class provides methods for:
 * - Retrieving tokens from iFrame context using AppBridge
 * - Managing token storage and expiration
 * - Handling OAuth callback token processing
 * - Token validation and session management
 */
export class TokenHelpers {
  /**
   * Retrieves an authentication token for applications running within ikas dashboard iFrame.
   * 
   * This method handles token retrieval through the ikas AppBridge when the application
   * is embedded within the ikas dashboard. It implements a caching mechanism using
   * sessionStorage to avoid unnecessary API calls and provides automatic token refresh
   * when cached tokens expire.
   * 
   * @returns {Promise<string | null>} A promise that resolves to:
   *   - A valid JWT token string if successfully retrieved
   *   - null if the app is not in an iFrame context or token retrieval fails
   * 
   * @throws Will log errors to console if AppBridge token retrieval fails
   * 
   * @remarks
   * - Only works when app is displayed in iFrame within ikas dashboard
   * - Will throw a timeout error if used outside iFrame context
   * - Automatically handles token caching and expiration validation
   * - Uses JWT payload decoding to check token expiration
   */
  static getTokenForIframeApp = async (): Promise<string | null> => {
    // Only proceed if running inside an iFrame (within ikas dashboard)
    if (window.self !== window.top) {
      try {
        // Get the authorized app ID to create a unique storage key
        const authorizedAppId = (await AppBridgeHelper.getAuthorizedAppId()) || null;
        
        // Attempt to retrieve cached token from session storage
        let token = sessionStorage.getItem(`${TOKEN_KEY}-${authorizedAppId}`);
        
        if (token) {
          // Decode JWT payload to check expiration (JWT structure: header.payload.signature)
          const tokenData = JSON.parse(atob(token.split('.')[1]));
          
          // Return cached token if it hasn't expired yet
          if (new Date().getTime() < tokenData.exp * 1000) {
            return token;
          }
          
          // Token has expired, remove from cache
          sessionStorage.removeItem(`${TOKEN_KEY}-${authorizedAppId}`);
        }
        
        // No valid cached token found, request new token from AppBridge
        token = (await AppBridgeHelper.getNewToken()) || null;
        
        if (token) {
          // Cache the new token for future use
          sessionStorage.setItem(`${TOKEN_KEY}-${authorizedAppId}`, token);
          return token;
        }
        
      } catch (error) {
        console.error('Error retrieving token from AppBridge:', error);
      }
    }
    
    // Return null if not in iFrame context or token retrieval failed
    return null;
  };

  /**
   * Processes OAuth callback parameters and handles token storage and redirection.
   * 
   * This method is typically called after an OAuth authorization flow completes.
   * It extracts the token from URL parameters, stores it in session storage,
   * and redirects the user to the specified redirect URL. If the required
   * parameters are missing, it redirects to the authorization page.
   * 
   * @param {ReturnType<typeof useRouter>} router - Next.js router instance for navigation
   * @param {URLSearchParams} params - URL search parameters containing OAuth callback data
   * 
   * @throws {string} Throws 'redirectUrl-called' after successful redirect to indicate flow completion
   * 
   * @remarks
   * - Expects 'token', 'redirectUrl', and 'authorizedAppId' parameters in the URL
   * - Stores both the token and authorized app ID in session storage
   * - Uses window.location.replace() for immediate redirection without history entry
   * - Falls back to authorization page if required parameters are missing
   */
  static setToken = async (
    router: ReturnType<typeof useRouter>, 
    params: URLSearchParams
  ): Promise<void> => {
    // Check if all required OAuth callback parameters are present
    const hasRequiredParams = params.has('token') && 
                             params.has('redirectUrl') && 
                             params.has('authorizedAppId');
    
    if (hasRequiredParams) {
      // Extract OAuth callback parameters
      const token = params.get('token')!;
      const authorizedAppId = params.get('authorizedAppId')!;
      const redirectUrl = params.get('redirectUrl')!;
      
      // Store token with app-specific key for future retrieval
      sessionStorage.setItem(`${TOKEN_KEY}-${authorizedAppId}`, token);
      
      // Store authorized app ID separately for reference
      sessionStorage.setItem('authorizedAppId', authorizedAppId);
      
      // Redirect to the specified URL (typically back to the app)
      window.location.replace(redirectUrl);
      
      // Throw to indicate successful redirect (prevents further execution)
      throw 'redirectUrl-called';
    }
    
    // Missing required parameters - redirect to authorization page
    await router.push('/authorize-store');
  };

  /**
   * Validates a code signature using HMAC-SHA256.
   *
   * This method is used to verify the authenticity of OAuth authorization codes
   * by comparing a received signature with an expected signature computed using
   * the client secret. This provides an additional layer of security to ensure
   * the code has not been tampered with.
   *
   * @param {string} code - The authorization code to validate
   * @param {string} receivedSignature - The signature received with the code
   * @param {string} secret - The client secret used to generate the expected signature
   *
   * @returns {boolean} True if the signatures match, false otherwise
   *
   * @remarks
   * - Uses HMAC-SHA256 algorithm for signature generation
   * - Compares signatures using strict equality
   * - Should be called before exchanging authorization code for tokens
   */
  static validateCodeSignature = (code: string, receivedSignature: string, secret: string): boolean => {
    const expectedSignature = crypto.createHmac('sha256', secret).update(code, 'utf8').digest('hex');
    return expectedSignature === receivedSignature;
  };
}
