export type TokenGetter = () => Promise<string | null>;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getToken: TokenGetter,
  ) {}

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = await this.getToken();
    const headers = new Headers(options.headers);
    // FormData bodies set their own multipart boundary — don't override it.
    if (!(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  postForm<T>(path: string, form: FormData): Promise<T> {
    return this.request<T>(path, { method: "POST", body: form });
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: "PUT", body: JSON.stringify(body) });
  }

  patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}
