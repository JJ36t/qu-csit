# Store Listing Checklist — Google Play

**App name (Arabic)**: علوم الحاسوب
**App name (English)**: QU CSIT
**Package ID**: `iq.edu.qu.csit`
**Target**: Google Play (Android)

## Required Assets

- [x] **App name**: علوم الحاسوب / QU CSIT
- [x] **Package ID**: `iq.edu.qu.csit` (set in `app/pubspec.yaml` + `flutter create --org iq.edu.qu.csit`)
- [x] **Privacy policy URL**: `https://<domain>/api/v1/public/privacy?lang=ar` (served by the API)
- [x] **App icon**: placeholder — needs design (College logo with permission)
- [x] **Feature graphic** (1024×500): placeholder — needs design
- [x] **Phone screenshots** (min 2, max 8): to be captured from running APK
- [x] **Short description** (80 chars max): "تطبيق كلية علوم الحاسوب — جامعة القادسية: الجدول، الحضور، المحاضرات، الإعلانات"
- [x] **Full description** (4000 chars max): see `STORE_DESCRIPTION.md` below
- [x] **App category**: Education
- [x] **Content rating**: Everyone (no mature content)
- [x] **Target audience**: University students (18+)
- [x] **Ads**: No ads
- [x] **In-app purchases**: None

## Data Safety Form (Google Play)

### Data collected:

| Data type | Purpose | Required | Encrypted in transit | Can request deletion |
|---|---|---|---|---|
| Personal info (name, university ID, email, phone) | Account management | Required | Yes (HTTPS) | Yes (on graduation) |
| Health and fitness (attendance records) | App functionality | Required | Yes | Yes |
| Approximate location (GPS at scan time only) | Attendance verification | Optional | Yes | Yes |
| Device or other IDs (device fingerprint, FCM token) | Account security + notifications | Required | Yes | Yes |

### Data NOT collected:

- ❌ Precise location (only approximate, at scan time)
- ❌ Background location
- ❌ Financial information
- ❌ Messages
- ❌ Photos and videos
- ❌ Audio recordings
- ❌ Web browsing history
- ❌ Contacts
- ❌ Calendar
- ❌ App activity (analytics)
- ❌ Crash logs (Sentry configured with `send_default_pii=False`)

### Data handling:

- **Encrypted in transit**: Yes (HTTPS + HSTS)
- **Can request deletion**: Yes (via department admin, on graduation)
- **Independent use**: Data is used only for the app's core functionality; not shared with third parties.

## Permissions (Android)

| Permission | Reason | Required |
|---|---|---|
| `INTERNET` | API communication | Yes |
| `ACCESS_NETWORK_STATE` | Offline detection | Yes |
| `CAMERA` | QR scanner for attendance | Yes |
| `ACCESS_FINE_LOCATION` | Attendance GPS verification (scan time only) | Optional |
| `ACCESS_COARSE_LOCATION` | Fallback for GPS | Optional |
| `POST_NOTIFICATIONS` (Android 13+) | Push notifications | Optional |
| `RECEIVE_BOOT_COMPLETED` | Reschedule reminders after reboot | Yes |
| `SCHEDULE_EXACT_ALARM` | Exact reminder scheduling | Yes |
| `USE_FULL_SCREEN_INTENT` | High-priority attendance notifications | Optional |
| `VIBRATE` | Notification feedback | Yes |

**No dangerous permissions beyond camera + location (both clearly justified).**

## Store Description (Arabic)

```
تطبيق كلية علوم الحاسوب وتكنولوجيا المعلومات — جامعة القادسية

يجمع التطبيق يومك الجامعي في مكان واحد:

• الجدول الأسبوعي مع القاعات والأوقات
• تسجيل الحضور بـ QR (آمن، يتجدّد كل 20 ثانية)
• المحاضرات (PDF + روابط الفيديو) مرتبة بالأسابيع
• الإعلانات الموجّهة (كلية، قسم، مرحلة، شعبة، مادة)
• الإشعارات الفورية لتغييرات الجدول والمحاضرات الجديدة
• تذكير قبل المحاضرات بـ 15 دقيقة + ملخص محاضرات الغد
• يعمل بإنترنت ضعيف (تخزين محلي للجدول والإعلانات)

الخصوصية:
• نجمع الحد الأدنى من البيانات
• الموقع يُرسل لحظة المسح فقط، ولا نتتبعك في الخلفية
• كلمة المرور محمية بـ Argon2id
• جهاز واحد لكل حساب طالب

التطبيق رسمي لكلية علوم الحاسوب وتكنولوجيا المعلومات — جامعة القادسية.
```

## Store Description (English)

```
College of Computer Science and IT App — University of Al-Qadisiyah

Your academic day, in one app:

• Weekly timetable with rooms and times
• QR attendance (secure, rotates every 20 seconds)
• Lecture materials (PDF + video links) organized by week
• Targeted announcements (college, department, stage, group, course)
• Push notifications for timetable changes and new materials
• 15-minute lecture reminders + tomorrow's lectures summary
• Works with weak internet (offline cache for timetable + announcements)

Privacy:
• Minimal data collection
• Location sent only at scan time; no background tracking
• Passwords protected with Argon2id
• One device per student account

Official app for the College of Computer Science and Information Technology — University of Al-Qadisiyah.
```

## Release Build

```bash
cd app
flutter build appbundle --release --obfuscate --split-debug-info=./build/symbols
# Upload the .aab to Play Console
```

## Signing

- **Keystore**: Generate a release keystore (NEVER commit it):
  ```bash
  keytool -genkey -v -keystore ~/csit-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias csit
  ```
- **`android/key.properties`** (gitignored):
  ```
  storePassword=***
  keyPassword=***
  keyAlias=csit
  storeFile=/path/to/csit-release.jks
  ```
- **`android/app/build.gradle`**: reads `key.properties` and signs the release build.

## Internal Testing Track

1. Upload the `.aab` to Play Console → Internal testing.
2. Add 5-20 testers (CSIT staff + student volunteers).
3. Collect feedback for 1 week.
4. Promote to Closed testing → Open testing → Production.
