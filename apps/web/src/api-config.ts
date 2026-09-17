const LOCAL_API_BASE_URL = "http://127.0.0.1:8010";

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

export function resolveApiBaseUrl(
  configuredUrl: string | undefined,
  isProduction: boolean,
  browserOrigin: string,
): string {
  const configured = configuredUrl?.trim();
  if (configured) return withoutTrailingSlash(configured);
  if (isProduction) return withoutTrailingSlash(browserOrigin);
  return LOCAL_API_BASE_URL;
}
