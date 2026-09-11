import { GetMerchantQueryData } from '@/lib/ikas-client/generated/graphql';
import { getIkas } from '@/helpers/api-helpers';
import { getUserFromRequest } from '@/lib/auth-helpers';
import { AuthTokenManager } from '@/models/auth-token/manager';
import { NextRequest, NextResponse } from 'next/server';

export type GetMerchantApiResponse = {
  merchantInfo?: GetMerchantQueryData;
};

/**
 * Handles GET requests to fetch merchant information for the authenticated user.
 * - Authenticates the user from the request.
 * - Retrieves the auth token for the user's authorized app.
 * - Fetches merchant info using the Ikas API client.
 * - Returns the merchant info or an appropriate error response.
 */
export async function GET(request: NextRequest,) {
  try {
    // Authenticate user from the request
    const user = getUserFromRequest(request);
    if (!user) {
      // User is not authenticated
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Retrieve the auth token for the user's authorized app
    const authToken = await AuthTokenManager.get(user.authorizedAppId);
    if (!authToken) {
      // Auth token not found for the user
      return NextResponse.json({ error: { statusCode: 404, message: 'Auth token not found' } }, { status: 404 });
    }

    // Initialize Ikas API client with the auth token
    const ikasClient = getIkas(authToken);

    // Fetch merchant information from Ikas API
    const merchantResponse = await ikasClient.queries.getMerchant();

    // Check if the API call was successful and merchant data is present
    if (merchantResponse.isSuccess && merchantResponse.data && merchantResponse.data.getMerchant) {
      // Return the merchant information
      return NextResponse.json({ data: { merchantInfo: merchantResponse.data.getMerchant } });
    } else {
      // Merchant not found or API call failed
      return NextResponse.json({ error: { statusCode: 403, message: 'Merchant not found' } }, { status: 403 });
    }
  } catch (error) {
    // Log the error for debugging
    console.error('Error fetching merchant:', error);
    // Return a generic server error response
    return NextResponse.json({ error: { statusCode: 500, message: 'Failed to fetch merchant' } }, { status: 500 });
  }
}
