---
name: store-submission-compliance
description: App Store and Google Play review rules for mobile apps — build, review, pre-submission audit.
---

# Store Submission Compliance

The rules that keep an iOS or Android build from coming back from App Store or Google Play review. They apply three times: while a feature is built (§ Build It Right), when its diff is reviewed (§ In a Code Review), and as a gate before the build goes to App Store Connect or the Play Console (§ Procedure), which ends with one verdict. It does not replace store review: a clean result means none of the known, preventable causes were found, not that the app will be approved.

ADR-0070 records why this skill is written here instead of vendored.

## When It Runs

| Moment | Who | What |
|---|---|---|
| Planning a feature for an app | `product-analyst` | Records the scope items in § Build It Right that the feature triggers (account deletion with sign-up, demo account, equivalent login, store billing for digital goods) as requirements |
| Designing a screen the store reviews | `ui-ux-designer` | Follows § Build It Right for paywalls, permission pre-prompts, sign-in options, the delete-account entry point and store screenshots |
| Building a change in a store-sensitive area | `mobile-developer`, from the start of the task | Builds what § Build It Right requires, then runs the code half before declaring done |
| Reviewing a diff that touches a store-sensitive area | Code reviewers (through `reviewer-base`); `qa-specialist` in its own report | Code half on the diff, severities mapped per § In a Code Review |
| A release, a submission, or a release branch | `qa-specialist` | Full audit: both halves and the verdict |
| The app was rejected | Whoever handles it | § After a Rejection |

**Store-sensitive area** — a change in an iOS or Android app's own code or configuration (never the backend that serves it) that touches any of: permissions or their usage strings; sign-up, sign-in or account deletion; purchases, subscriptions or a paywall; analytics, ads, attribution, crash or AI SDKs; personal data sent to a third party; user-generated content; `Info.plist`, entitlements, the privacy manifest, the Android manifest, the app module's Gradle or Xcode build settings; backend base URLs or build flavours; a web view that renders the app's main content. A change to the app's store listing text or screenshots counts too.

**iOS or Android target** means any of: `*.xcodeproj` / `*.xcworkspace`, `Info.plist`, an `ios/` or `android/` folder, `AndroidManifest.xml`, `build.gradle(.kts)`, or a Flutter, React Native / Expo, Capacitor / Cordova, .NET MAUI or Kotlin Multiplatform project that builds one.

## Build It Right

Build these together with the feature that triggers them. A feature merged without its row's requirement is unfinished, not a later store fix.

| When the change adds or touches | Build in the same change | Rule |
|---|---|---|
| Sign-up or any account creation | In-app delete-account flow that removes the account and its data; on Android also a web deletion page | Apple 5.1.1(v), Play Account deletion |
| An app behind a login | A reviewer account with sample data, kept working on production; its credentials go in the review notes, never in code | Apple 2.1(a), Play app access |
| A third-party or social login as the main sign-in | A privacy-focused equivalent (Sign in with Apple, or one meeting 4.8) on iOS | Apple 4.8 |
| A permission request | A usage string naming the feature; the request at the moment of use, not at launch; a pre-prompt button labelled "Continue", never "Allow"; on Android, a prominent disclosure screen before sensitive or background data | Apple 5.1.1(ii)/(iv), Play User Data |
| A restricted Android permission (background location, SMS or call log, all files, media, accessibility, overlay, `QUERY_ALL_PACKAGES`) | The narrower alternative first (foreground location, SMS Retriever, system picker, `<queries>`); the permission only for a core feature, with its Console declaration noted in the PR | Play permission policies |
| A new SDK or library | Its privacy manifest present (iOS); the data it collects added to the PR description for App Privacy and Data safety; tracking only after App Tracking Transparency | Apple privacy manifest, 5.1.2; Play Data safety |
| Personal data sent to an AI or other third-party service | A disclosure naming the recipient and an explicit consent before the first send | Apple 5.1.2 |
| Selling digital content, features or subscriptions | StoreKit / Play Billing (current library version); a restore control; benefits, billed amount and period shown before purchase; terms and privacy links on the paywall; external purchase links only where allowed | Apple 3.1.1–3.1.3, Play Payments |
| User-generated content | Filter, report with a timely response, block users, published contact | Apple 1.2, Play UGC |
| Generative AI output | In-app report or flag action and output safeguards | Apple 1.2, Play AI-Generated Content |
| Backend URLs or build flavours | Release flavour points at production; staging and debug tools compiled out of release | Apple 2.1(a) and 2.5.19 (debug UI), Play Minimum functionality |
| Store screenshots or previews | This build in use, not a splash or login screen, for every device family offered | Apple 2.3.3; manual check `screenshots_match_build` |
| Build targets or SDK versions | Target API, upload SDK and Billing Library at or above the floors in the references | References § Volatile Facts |
| A web view as the main surface | Native value beyond the website (push, offline, device features, native navigation) | Apple 4.2 |

## In a Code Review

A reviewer runs the code half against the **diff only** (pre-existing code is out of scope unless the diff makes it reachable) and reports each hit in `skills/shared/review-result/SKILL.md` § Findings Table with its signal ID:

| Skill severity | Review severity |
|---|---|
| `CRITICAL` | `BLOCKING` |
| `HIGH` | `SUGGESTION` (the `review-result` mapping); it still blocks the submission verdict unless the PR records why it does not apply |
| `MEDIUM` | `SUGGESTION` |
| `MANUAL` | Not a finding: listed under "Manual checks before submission" in the review summary |

A § Build It Right requirement missing from a diff that triggers it is reported under the matching signal ID (for example sign-up without deletion as `IOS-ACCOUNT-DELETION` / `AND-ACCOUNT-DELETION`), or under the `TYPE-<app type>` fallback in § Severity when no ID exists (UGC, AI output).

## Where to Read Each Signal

| Stack | iOS config | Android config |
|---|---|---|
| Native | `Info.plist`, `*.entitlements`, `PrivacyInfo.xcprivacy`, the Xcode project | The merged manifest, `build.gradle(.kts)` |
| Flutter | `ios/Runner/Info.plist`, `ios/Runner/*.entitlements` | `android/app/src/main/AndroidManifest.xml`, `android/app/build.gradle(.kts)` |
| Expo managed | `app.json` / `app.config.*`: `ios.infoPlist`, `ios.entitlements`, `ios.privacyManifests` (no committed `ios/` folder; `npx expo prebuild` output when present) | `app.json` / `app.config.*`: `android.permissions`, `android.blockedPermissions`, plugin config |
| React Native bare, Capacitor, Cordova | `ios/` as native | `android/` as native |

## The Two Halves

Report them separately. One never stands in for the other.

| Half | What it covers | Proven by |
|---|---|---|
| **Code** | What the repository shows: manifests, `Info.plist`, entitlements, the privacy manifest, Gradle and Xcode settings, dependencies, release-build constants, sign-in, purchase and deletion code | The agent, reading the project against the signal tables in the references |
| **Manual** | What only the running release build, the store listing and the review notes show | A person, on the release build, recorded in § Manual Checks |

Most painful rejections live in the manual half. Never report the app ready while a manual check is still `todo`.

## Procedure

1. **Detect the targets.** List each app root and its platforms. In a monorepo, audit each app on its own.
2. **Classify the app.** Pick every row that applies in `references/by-app-type.md` (account-based, subscriptions, UGC, AI features, kids, health, finance, games with paid random items, VPN). Load only those rows.
3. **Check freshness.** Each volatile fact in the references carries a `verified` date. A fact verified more than 60 days ago is re-read at its source URL before it can raise a `CRITICAL`. If the source cannot be read, report the finding as `HIGH` with "unverified since <date>".
4. **Run the code half.** Load `references/apple.md` for an iOS target and `references/google-play.md` for an Android target. Walk each signal table against the project. Record every hit with its file and line.
5. **Run the manual half.** Skip it on a code-half-only run (no questions, no Open Decisions). Otherwise ask for, or read from a previous report for the same build, each item in § Manual Checks. A sub-agent cannot ask the user: it lists the open items under `## Open Decisions` (`skills/shared/interaction-patterns/SKILL.md` § Sub-agent Question Relay).
6. **Write the report** in the format below and give the verdict.

Every signal is a lead, not a verdict. Confirm in the code that the hit is real: a staging URL inside a debug-only block, or a permission that a dependency declares and the merged manifest removes, is not a finding.

## Severity

| Severity | Meaning | Effect |
|---|---|---|
| `CRITICAL` | Review rejects the build, the upload is refused, or the store removes the app | Blocks submission |
| `HIGH` | Likely rejection, or a store form that will not match the build | Blocks unless a person records why it does not apply |
| `MEDIUM` | Possible rejection or a review question; fix when cheap | Listed, does not block |
| `MANUAL` | A reviewer judgement no code can decide (Apple 4.2, 4.3) | Reported under Manual checks as `todo` until a person rules on it |

Rows in `references/by-app-type.md` carry no IDs of their own: report a hit under the matching ID in `apple.md` or `google-play.md`, or, when none exists, as `TYPE-<app type>` with severity `HIGH`.

## Manual Checks

Record each as `pass`, `fail`, `todo` or `n/a`, with the build number and the date it was checked, in the Manual checks table of the report. `n/a` needs a one-line reason. A later run may reuse a previous report's entries only for the same build; a new build starts every check at `todo`.

| Check | Platform | What proves it |
|---|---|---|
| `demo_account` | Both | A reviewer account that signs in on the release build, with data in it, written in the review notes (Apple 2.1(a); Play app access instructions). A demo mode replaces it only where Apple approved that in advance |
| `live_backend` | Both | The production backend answers the release build and will stay up through the review window |
| `review_notes` | Both | The notes say where each non-obvious feature is, which hardware or region it needs, and how to reach anything behind a login or paywall |
| `screenshots_match_build` | Both | Screenshots show this build in use, not a splash or login screen, for every device family offered (Apple 2.3.3) |
| `account_deletion_device_test` | Both | On a device: the account is deleted from inside the app, and signing in again does not bring it back |
| `privacy_labels_match_runtime` | Both | App Privacy answers (Apple) and the Data safety form (Play) match what the build and every SDK actually send. Never `n/a` |
| `purchase_reachable` | Both | The reviewer can reach and complete each in-app purchase or subscription in the sandbox |
| `age_rating_answered` | Both | The current age-rating questionnaire is answered for this build |
| `closed_test_done` | Android | For a personal Play account created after 2023-11-13: a closed test with 12 or more testers opted in for 14 days in a row |

## Report Format

Follow `skills/shared/output-format/SKILL.md`.

```markdown
## Store Submission Compliance — <app> <version> (<build>)

**Targets:** iOS, Android · **App types:** account-based, subscriptions
**Rules verified:** oldest <date>, newest <date> · <N> facts re-read this run

### Code findings
| Severity | ID | Platform | Rule | File | Fix |
|---|---|---|---|---|---|

### Manual checks
| Check | Status | Build | Checked on | Note |
|---|---|---|---|---|

### Verdict
BLOCKED — 2 critical, 1 manual check failed.
1. <numbered fix list, criticals first>
```

| Verdict | When |
|---|---|
| `CLEAR` | No `CRITICAL`, no unexplained `HIGH`, and every manual check is `pass` or `n/a` for this build |
| `BLOCKED` | Any `CRITICAL`, any unexplained `HIGH`, or any manual check `fail` |
| `NOT CHECKED` | No iOS or Android target was found, or the manual half is still `todo`. Never treated as a pass |

`BLOCKED` wins over `NOT CHECKED`. A code-half-only run (`mobile-developer`) gives no verdict: it reports `Code half: <N> findings (<C> critical)` with the Code findings table, and leaves the verdict to QA.

When `qa-specialist` runs this skill, a `BLOCKED` verdict is a `[BLOCKER]` in its QA report, listing each cause.

## After a Rejection

1. Take the exact guideline or policy the rejection cites and find its row in the references.
2. Fix the cause, then run this skill again on the new build. Never resubmit an unchanged build: on Play, repeated policy violations count against the developer account.
3. Answer the reviewer point by point (Resolution Center on Apple, the appeal form on Play). Say what changed and where to find it; attach a short screen recording when the issue is about behaviour.
4. Some rejections cannot be decided from the code, such as Apple 4.3 spam or a judgement call on 4.2 minimum functionality. Report those as manual items; no static check can rule on them.

## References

| File | Load when |
|---|---|
| `references/apple.md` | The app has an iOS, iPadOS or macOS App Store target |
| `references/google-play.md` | The app has an Android target distributed on Google Play |
| `references/by-app-type.md` | Always, then only the rows the app matches |
