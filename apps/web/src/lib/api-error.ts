export class ApiError<TBody = unknown> extends Error {
  readonly status: number;
  readonly body: TBody;
  readonly url?: string;
  readonly detail?: string;

  constructor(status: number, message: string, body: TBody, url?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.url = url;
    const rawDetail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail?: unknown }).detail
        : undefined;
    this.detail = typeof rawDetail === "string" ? rawDetail : message;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
