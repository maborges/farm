export class ApiError<TBody = unknown> extends Error {
  readonly status: number;
  readonly body: TBody;
  readonly url?: string;

  constructor(status: number, message: string, body: TBody, url?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.url = url;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
