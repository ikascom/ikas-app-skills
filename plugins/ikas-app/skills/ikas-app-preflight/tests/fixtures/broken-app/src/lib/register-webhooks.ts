import { getIkas } from '@/helpers/api-helpers';
import { AuthToken } from '@/models/auth-token';

// §6.2 / §6.3: store/app/deleted cannot be registered with saveWebhooks (INVALID_SCOPE); it comes from the Partner-panel Bildirim Adresi
export async function registerWebhooks(authToken: AuthToken, deployUrl: string) {
  return getIkas(authToken).mutations.saveWebhooks({
    input: { endpoint: `${deployUrl}/api/webhooks/ikas`, scopes: ['store/order/created', 'store/app/deleted'] },
  });
}
