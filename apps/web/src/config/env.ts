const DEFAULT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export function getPublicApiBaseUrl(): string {
  const configuredValue = process.env.NEXT_PUBLIC_MANGAI_API_URL?.trim();
  return configuredValue && configuredValue.length > 0
    ? configuredValue.replace(/\/+$/, "")
    : DEFAULT_PUBLIC_API_BASE_URL;
}
