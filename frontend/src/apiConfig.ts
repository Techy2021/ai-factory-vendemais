const LOCAL_API_BASE = "http://localhost:8001";

export function resolveApiBase(configuredUrl: string | undefined, development: boolean): string {
  let value = configuredUrl?.trim();
  let browserOrigin = false;
  if (!value) {
    if (development) return LOCAL_API_BASE;
    if (typeof window === "undefined") {
      throw new Error("Não é possível determinar a origem da API sem contexto de navegador.");
    }
    value = window.location.origin;
    browserOrigin = true;
  }

  const invalidUrlMessage = browserOrigin
    ? "A origem do navegador deve ser uma origem HTTPS válida em produção."
    : "VITE_API_BASE_URL deve ser uma origem HTTP(S) válida.";
  const unsafeUrlMessage = browserOrigin
    ? "A origem do navegador deve ser uma origem HTTPS válida em produção."
    : "VITE_API_BASE_URL deve ser uma origem HTTPS sem credenciais, caminho, consulta ou fragmento; HTTP é permitido apenas em desenvolvimento local.";

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(invalidUrlMessage);
  }

  const localHttp = development && url.protocol === "http:"
    && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (
    (url.protocol !== "https:" && !localHttp)
    || url.username || url.password
    || url.pathname !== "/" || url.search || url.hash
  ) {
    throw new Error(unsafeUrlMessage);
  }

  return url.origin;
}
