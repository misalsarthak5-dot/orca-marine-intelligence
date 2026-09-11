/**
 * ORCA — Centralized API Configuration
 * 
 * Unified FastAPI backend base URL resolution across all frontend services.
 * Prioritizes NEXT_PUBLIC_FASTAPI_BASE_URL -> NEXT_PUBLIC_FASTAPI_URL -> http://127.0.0.1:8000
 */

export const FASTAPI_BASE_URL: string =
  process.env.NEXT_PUBLIC_FASTAPI_BASE_URL ||
  process.env.NEXT_PUBLIC_FASTAPI_URL ||
  'http://127.0.0.1:8000';

export function getApiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${FASTAPI_BASE_URL}${cleanPath}`;
}
