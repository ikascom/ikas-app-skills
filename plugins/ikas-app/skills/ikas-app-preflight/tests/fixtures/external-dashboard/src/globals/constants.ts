export const TOKEN_COOKIE = '_session_data';

export type ApiErrorData = {
  statusCode: number;
  message: string;
};

export type ApiErrorResponse = {
  statusCode: number;
  message: string;
};

export type ApiResponseType<T> =
  | {
      data?: T;
      error?: ApiErrorResponse;
    }
  | undefined;
