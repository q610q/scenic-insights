/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_TARGET: string
  readonly VITE_AMAP_JSAPI_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
