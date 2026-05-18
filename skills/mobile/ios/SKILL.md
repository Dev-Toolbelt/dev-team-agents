---
name: ios
description: iOS-specific development guidelines — design, permissions, code signing, and native Swift/SwiftUI standards. Load when the project targets iOS.
---

## Design & UX

- Load `skills/mobile/ios-hig/SKILL.md` for the full reference on navigation patterns, controls, typography (Dynamic Type / SF Pro), layout (Safe Area), Dark Mode, and accessibility (VoiceOver, Reduce Motion)
- Respect the **Safe Area** — never place interactive elements behind notches, home indicators, or Dynamic Island
- Support **Dynamic Type** — use semantic text styles (`UIFont.preferredFont`, `Text().font(.body)`) instead of fixed sizes
- Support both light and dark mode using semantic system colors only

## Permissions & Privacy

- Request permissions only at the moment they are first needed (not at launch)
- Provide a clear in-app rationale before the OS permission dialog appears
- Handle all permission states: `notDetermined`, `authorized`, `denied`, `restricted`
- Populate every required `NSUsageDescription` key in `Info.plist` before submitting to App Store
- **Privacy Manifest** (`PrivacyInfo.xcprivacy`): required for apps using certain APIs (file timestamps, user defaults, disk space) — add it before App Store submission

## Code Signing & Distribution

- Always use **Automatic Signing** in Xcode for development; switch to **Manual Signing** for CI/CD
- Distribution certificate + provisioning profile must match the `bundleIdentifier` exactly
- Use **TestFlight** for all pre-production builds — never distribute `.ipa` files directly
- Increment `CFBundleVersion` (build number) for every TestFlight build; increment `CFBundleShortVersionString` only for user-visible releases

## Native Swift / SwiftUI Standards

- Prefer **SwiftUI** for new screens; use **UIKit** only when SwiftUI cannot achieve the required behavior
- Use `@StateObject` for objects owned by the view, `@ObservedObject` for injected objects, `@EnvironmentObject` for app-wide state
- `async/await` over completion handlers for all new async code
- Never force-unwrap (`!`) without a guard or a comment justifying why it cannot be nil
