import type { HealthResponse } from "@/types/api";

type AuthUser = {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
};

type AuthTokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

type LogoutResponse = {
  message: string;
};

let accessToken: string | null = null;

function requireBrowserTokenStorage(): void {
  if (typeof window === "undefined") {
    throw new Error("Bearer tokens may only be stored in browser memory.");
  }
}

function getApiBaseUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  }

  return apiUrl.replace(/\/+$/, "");
}

export function setAccessToken(token: string): void {
  requireBrowserTokenStorage();
  if (!token.trim()) {
    throw new Error("An access token cannot be empty.");
  }
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (typeof window !== "undefined" && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(
    `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`,
    { ...init, headers },
  );
  if (response.status === 401) {
    clearAccessToken();
  }
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}).`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
}

export async function login(
  email: string,
  password: string,
): Promise<AuthTokenResponse> {
  requireBrowserTokenStorage();
  const result = await apiRequest<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(result.access_token);
  return result;
}

export async function getCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/auth/me");
}

export async function logout(): Promise<LogoutResponse> {
  requireBrowserTokenStorage();
  try {
    return await apiRequest<LogoutResponse>("/api/v1/auth/logout", {
      method: "POST",
    });
  } finally {
    clearAccessToken();
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/health`);

  if (!response.ok) {
    throw new Error(`Backend health check failed (${response.status}).`);
  }

  return response.json() as Promise<HealthResponse>;
}
