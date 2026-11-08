// Тонкая обёртка над fetch: токен, ошибки в формате API, повтор после 401.

const BASE: string = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'swipe_token';

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let token: string | null = localStorage.getItem(TOKEN_KEY);
export const getToken = () => token;
export function setToken(value: string | null) {
  token = value;
  if (value) localStorage.setItem(TOKEN_KEY, value);
  else localStorage.removeItem(TOKEN_KEY);
}

// AuthContext регистрирует функцию, которая выдаёт новый гостевой токен
let unauthorizedHandler: (() => Promise<void>) | null = null;
export function onUnauthorized(fn: () => Promise<void>) {
  unauthorizedHandler = fn;
}

type Query = Record<string, string | number | boolean | null | undefined>;
type Options = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Query;
  auth?: boolean;
  keepalive?: boolean;
};

export async function request<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const url = new URL(BASE.replace(/\/$/, '') + path, window.location.origin);
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  }
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  if (token && opts.auth !== false) headers['Authorization'] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(url.toString(), {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      keepalive: opts.keepalive,
    });
  } catch {
    throw new ApiError(0, 'network', 'Нет соединения с сервером');
  }

  if (res.status === 401 && !retried && unauthorizedHandler && opts.auth !== false) {
    try {
      await unauthorizedHandler();
      return request<T>(path, opts, true);
    } catch {
      /* падаем ниже с обычной ошибкой */
    }
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: any = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = undefined;
    }
  }
  if (!res.ok) {
    const err = data?.error;
    throw new ApiError(res.status, err?.code ?? `http_${res.status}`, err?.message ?? 'Что-то пошло не так');
  }
  return data as T;
}
