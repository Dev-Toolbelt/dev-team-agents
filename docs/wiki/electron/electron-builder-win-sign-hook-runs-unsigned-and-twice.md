# electron-builder's `win.signtoolOptions.sign` hook runs for every executable, even unsigned, and twice by default

**Origin:** Windows signing through SSL.com eSigner in `app/build/sign-windows.cjs` (ADR-0055) | 2026-10-31
**Tags:** electron-builder, signtoolOptions.sign, signingHashAlgorithms, WIN_CSC_LINK, CSC_LINK, getCscLink, sign hook, dist:all

> A custom `win.signtoolOptions.sign` hook is called for every Windows executable even when no certificate is configured, and once per hash algorithm. The hook must no-op itself without credentials, and a Mac certificate must never reach the Windows path.

---

## How it works

1. electron-builder calls the hook for each Windows binary: the app exe, the uninstaller and the installers.
2. A custom `sign` bypasses electron-builder's "no signing info, skip" return, so the hook runs on unsigned local builds too.
3. The hook is called once per entry in `signingHashAlgorithms`. The default `sha1` plus `sha256` produces two signatures per file.
4. The second argument is the `Packager`, not an options object. Never read options from it.
5. The Windows certificate lookup (`platformPackager.getCscLink`) falls back from `WIN_CSC_LINK` to `CSC_LINK`.

## Gotchas

- Return early inside the hook when the signing credentials are absent. Relying on electron-builder to skip it does not work.
- Set `signingHashAlgorithms: ["sha256"]` to get one signature per file.
- On a Mac, `CSC_LINK` often holds the macOS `.p12`. `dist:all` then hands that Mac certificate to the Windows path through the fallback. Set `WIN_CSC_LINK` explicitly for Windows builds.

## References

- `app/build/sign-windows.cjs`
- `docs/development/adrs/0055-windows-code-signing-goes-through-ssl-com-esigner-a-cloud-hsm-not-a-pfx.md`
