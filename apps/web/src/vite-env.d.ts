/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_STATIC_SITE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

