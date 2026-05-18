---
name: android
description: Android-specific development guidelines — design, permissions, release signing, and native Kotlin/Jetpack Compose standards. Load when the project targets Android.
---

## Design & UX

- Load `skills/mobile/material-design/SKILL.md` for the full reference on color system (Material You tokens), typography scale, components (NavigationBar, FAB, Cards, Bottom Sheet), motion, adaptive layout (Window Size Classes), and accessibility (48dp touch targets, TalkBack)
- Support **edge-to-edge** layout — use `WindowInsets` to avoid overlap with system bars
- Use **adaptive icons** (`mipmap-anydpi-v26/`) — required for Android 8.0+
- Support **back gesture** (predictive back on Android 14+) — register `OnBackPressedCallback` instead of overriding `onBackPressed()`
- Test on both small screens (< 5") and large screens / foldables

## Permissions & Privacy

- Declare only the permissions you actually use in `AndroidManifest.xml`
- Request runtime permissions with `ActivityResultContracts.RequestPermission`
- Handle `shouldShowRequestPermissionRationale()` — show an explanation before re-requesting
- Target the latest stable `targetSdkVersion` required by Google Play
- Fill the **Data Safety** section in Play Console accurately — it is legally binding

## Code Signing & Release

- The upload keystore must be stored securely (EAS Credentials, 1Password, or CI secret store) — **never commit it to the repository**
- Use **Android App Bundle (AAB)** for Play Store submissions — not APK
- Enable **R8/ProGuard** for release builds; test the release build locally before submitting to catch missing keep rules
- `versionCode` must be monotonically increasing — Play Store rejects builds with the same or lower version code

## Native Kotlin / Jetpack Compose Standards

- Prefer **Jetpack Compose** for new screens; use **Views/XML** only when Compose cannot achieve the required behavior or when maintaining existing View-based code
- Use `ViewModel` + `StateFlow`/`SharedFlow` for UI state — never hold state in Activities or Fragments
- Use **Room** for local persistence; **DataStore** for preferences (not SharedPreferences for new code)
- `suspend` functions and `Flow` over callbacks for all new async code
- Never run network or database operations on the main thread
