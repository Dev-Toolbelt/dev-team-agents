/**
 * What Vite returns for an imported image: the emitted asset's URL.
 *
 * Its own file, with no top-level import, because a wildcard `declare module` is only
 * ambient in a script — put it in `global.d.ts`, which imports a type, and TypeScript
 * reads it as a module augmentation and the import stays unresolved.
 *
 * Declared narrowly instead of via `/// <reference types="vite/client" />`, because
 * `tsconfig.web.json` sets `"types": []` on purpose: pulling Vite's ambient package in
 * would also declare `import.meta.env`, the HMR API and every other asset extension for
 * a renderer that deliberately uses none of them. Only the extensions actually imported
 * are listed, so a typo in one is a compile error rather than an `any`.
 */
declare module '*.png' {
  const url: string;
  export default url;
}
