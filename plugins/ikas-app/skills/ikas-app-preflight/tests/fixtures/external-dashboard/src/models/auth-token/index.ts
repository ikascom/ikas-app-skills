export interface AuthToken {
  id: string;
  merchantId: string;
  authorizedAppId?: string;
  salesChannelId: string | null;
  type?: string;
  createdAt?: string;
  updatedAt?: string;
  deleted?: boolean;

  accessToken: string;
  tokenType: string;
  expiresIn: number;
  expireDate: string;
  refreshToken: string;
  scope?: string;
}
