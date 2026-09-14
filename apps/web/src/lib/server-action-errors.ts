const STALE_SERVER_ACTION_MESSAGE = /failed to find server action|server action .* not found|older or newer deployment/i;

export function isStaleServerActionError(error: unknown): boolean {
    if (typeof error === "string") {
        return STALE_SERVER_ACTION_MESSAGE.test(error);
    }

    if (error instanceof Error) {
        return STALE_SERVER_ACTION_MESSAGE.test(error.message);
    }

    if (error && typeof error === "object" && "message" in error) {
        return STALE_SERVER_ACTION_MESSAGE.test(String(error.message));
    }

    return false;
}
