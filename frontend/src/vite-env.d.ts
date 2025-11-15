/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly __VITE_API_URL__: string
  readonly __VITE_WS_URL__: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}