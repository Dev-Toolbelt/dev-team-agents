# Apple App Store — Signals and Rules

Rules come from the App Store Review Guidelines and Apple Developer pages. Guideline numbers are cited so a finding can be matched to a rejection letter. Every row is a lead to confirm in code, not a verdict.

## Volatile Facts

Re-read the source when `verified` is more than 60 days old (SKILL.md § Procedure, step 3).

| Fact | Value | Source | Verified |
|---|---|---|---|
| Minimum SDK for uploads | iOS / iPadOS 26 SDK since 2026-04-28; iOS / iPadOS 27 SDK (targeting iOS 15 or later) from April 2027 | https://developer.apple.com/app-store/submitting/ · https://developer.apple.com/news/?id=ueeok6yw | 2026-11-25 |
| Age-rating questionnaire | Social media questions required for new submissions and updates since September 2026; Shared Location and Dating and Relationships declarations required for all apps by 2027-01-12 (Dating sets 18+) | https://developer.apple.com/news/?id=tlur8uvi · https://developer.apple.com/news/?id=yxkh08us | 2026-11-25 |
| Guideline changes of 2026-10-16 | 2.5.19 (hidden or dormant features, moved out of 2.3.1), 2.3.14 (creative assets), 1.2 extended to non-consensual intimate imagery including AI-generated | https://developer.apple.com/app-store/review/guidelines/ | 2026-11-25 |
| Privacy manifest for listed SDKs | Apps that include an SDK on Apple's list must ship that SDK's privacy manifest (and its signature for binary SDKs) in new apps and in updates that add it | https://developer.apple.com/support/third-party-SDK-requirements/ | 2026-11-25 (no enforcement date on the page) |
| External purchase links | Allowed in apps on the US storefront without an entitlement; elsewhere only with a StoreKit External Purchase Link entitlement for that region | https://developer.apple.com/app-store/review/guidelines/ (3.1.1(a), 3.1.3) | 2026-11-25 |
| Export compliance key | `ITSAppUsesNonExemptEncryption` in `Info.plist` answers the encryption question for every build; without it App Store Connect asks on each build and holds it until answered | https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations | Not re-verified (page did not render on 2026-11-25) |

## App Completeness and Build (2.1, 2.5)

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `IOS-STAGING-BACKEND` | CRITICAL | 2.1(a) | A base URL with `localhost`, `127.0.0.1`, `staging`, `dev`, `test` or an ngrok-style host compiled into the release configuration (not inside `#if DEBUG` or a debug-only flavour) | Point the release configuration at production |
| `IOS-PLACEHOLDER` | HIGH | 2.1(a) | `Lorem ipsum`, `TODO`, `placeholder`, `test` strings in user-facing resources, empty screens, sample images | Replace with final content |
| `IOS-DEBUG-UI` | HIGH | 2.1, 2.5.19 | Debug menus, feature-flag panels, environment switchers or test buttons reachable in release | Compile them out of release |
| `IOS-HIDDEN-FEATURE` | CRITICAL | 2.5.19 | Remote flags that switch on features not shown to review, server-driven UI that changes the app's purpose after approval | Ship only what review can see; document every flag-gated feature in the review notes |
| `IOS-PRIVATE-API` | HIGH | 2.5.1 | `NSSelectorFromString` / `performSelector` on private selectors, `dlopen` of private frameworks, `valueForKey:` on private UIKit properties | Use public API only |
| `IOS-DOWNLOADED-CODE` | CRITICAL | 2.5.2 | Downloading and running native code or scripts that change the app's features; an over-the-air JS updater that ships new features rather than fixes | Ship features in the binary; restrict OTA updates to bug fixes in already-reviewed code |
| `IOS-UIWEBVIEW` | CRITICAL | Upload refused (ITMS-90809) | Any `UIWebView` symbol, including from a dependency | Move to `WKWebView`; upgrade the dependency |
| `IOS-IPV4-ONLY` | MEDIUM | 2.5 | Hard-coded IPv4 literals, `inet_addr`, sockets bound to `AF_INET` only | Use host names and `Network` / `URLSession`; review runs on an IPv6-only network |
| `IOS-OLD-SDK` | CRITICAL | Upload requirement | Xcode project or CI image builds with an SDK older than § Volatile Facts | Upgrade Xcode on the build machine |
| `IOS-EXPORT-COMPLIANCE` | HIGH | Export compliance | `ITSAppUsesNonExemptEncryption` missing from `Info.plist` | Set it (`false` when only exempt encryption such as HTTPS is used) |
| `IOS-CLOUDKIT-DEV` | CRITICAL | 2.1 | CloudKit used but the schema was never deployed to production (`com.apple.developer.icloud-container-environment` = `Development` in release entitlements) | Deploy the schema to production before submission |
| `IOS-UNUSED-ENTITLEMENT` | HIGH | 2.5.4 | Entitlements or background modes in the `.entitlements` / `Info.plist` with no code using them | Remove what is not used |

## Privacy (5.1)

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `IOS-PURPOSE-STRING-MISSING` | CRITICAL | 5.1.1(ii) | A framework call that needs consent (camera, microphone, photos, location, contacts, calendars, Bluetooth, motion, health, speech, local network, Face ID) with no matching `NS…UsageDescription` key | Add the key |
| `IOS-PURPOSE-STRING-VAGUE` | HIGH | 5.1.1(ii) | A purpose string that is empty, generic ("needs access", "required") or does not name the feature | Say what the feature does with the data |
| `IOS-PRE-PROMPT-ALLOW` | MEDIUM | 5.1.1(iv) | A custom screen before the system prompt whose button says "Allow" or otherwise pushes consent | Label it "Continue" or "Next"; never pre-empt the system choice |
| `IOS-PRIVACY-MANIFEST` | CRITICAL | Privacy manifest | `PrivacyInfo.xcprivacy` missing while the app or a dependency uses required-reason APIs (`UserDefaults`, file timestamps, system boot time, disk space, active keyboards), or a listed SDK ships without its manifest | Add the app manifest with reason codes; upgrade the SDK to a version that ships one |
| `IOS-PRIVACY-POLICY` | CRITICAL | 5.1.1(i) | No privacy-policy URL in the app (settings, sign-up, about) | Link it in the app and in App Store Connect |
| `IOS-ACCOUNT-DELETION` | CRITICAL | 5.1.1(v) | Sign-up exists but no delete-account flow; deletion only by email, form or support ticket; deactivation offered as deletion | Let the user start deletion inside the app; a web flow is acceptable only through a direct link from the app |
| `IOS-UNNEEDED-DATA` | HIGH | 5.1.1(ii)/(iii) | Sign-up demands data the core feature does not use (phone, birth date, address) | Make it optional or drop it |
| `IOS-ATT-MISSING` | HIGH | 5.1.2 | Advertising or attribution SDK (ad networks, MMPs) or IDFA access without `ATTrackingManager.requestTrackingAuthorization` and `NSUserTrackingUsageDescription` | Request tracking permission before any tracking |
| `IOS-AI-SHARING` | HIGH | 5.1.2 | Personal data sent to a third-party AI service with no disclosure and explicit consent before the first send | Show who receives what, and ask first |

## Payments (3.1)

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `IOS-EXTERNAL-PAYMENT` | CRITICAL | 3.1.1 | A payment SDK or checkout web view (Stripe, PayPal, Mercado Pago, Pix) used to unlock digital content, features or subscriptions, with no StoreKit | Sell digital goods through in-app purchase; goods and services used outside the app are exempt (3.1.3(e)) |
| `IOS-EXTERNAL-LINK-REGION` | HIGH | 3.1.1(a), 3.1.3 | A "buy on our website" button or link shown on every storefront | Show it only on the US storefront or where the app holds the regional entitlement |
| `IOS-RESTORE` | HIGH | 3.1.1 | Non-consumable purchases or subscriptions with no restore action | Add a restore control |
| `IOS-SUBSCRIPTION-TERMS` | HIGH | 3.1.2(c) | The paywall does not state what the user gets, the billed amount and period, or shows a per-month equivalent larger than the billed price | State benefits, billed amount and period first; link the terms and privacy policy |
| `IOS-SUBSCRIPTION-PERIOD` | MEDIUM | 3.1.2(a) | Auto-renewing period under seven days, or subscription content not available on all the user's devices | Fix the product setup |

## Sign-In and Design (4)

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `IOS-LOGIN-EQUIVALENT` | HIGH | 4.8 | Google, Facebook or another third-party login as the main sign-in with no privacy-focused equivalent (Sign in with Apple, or one that meets 4.8's criteria) | Add the equivalent option, unless an exception in 4.8 applies |
| `IOS-WEB-WRAPPER` | MANUAL | 4.2 | The app is a web view around a website with no native feature (push, offline, device APIs, native navigation) | Add real app value; a reviewer judgement |
| `IOS-SPAM` | MANUAL | 4.3 | Many near-identical apps from one account, template or white-label apps | Not decidable from code; manual item |

## Metadata (2.3)

Read the store listing text (fastlane `metadata/`, App Store Connect export, or ask) when it is available.

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `IOS-META-OTHER-PLATFORM` | MEDIUM | 2.3.10 | "Android", "Google Play" or other platforms named in the listing or in iOS UI strings | Remove them |
| `IOS-META-OVERPROMISE` | MEDIUM | 2.3.1(a) | The listing describes features this build does not ship | Describe only what ships |
| `IOS-META-SCREENSHOTS` | HIGH | 2.3.3 | Screenshots of a splash, login or title art only | Show the app in use |
| `IOS-AGE-RATING` | HIGH | 2.3.6 | The questionnaire not answered against § Volatile Facts | Answer it in App Store Connect |
