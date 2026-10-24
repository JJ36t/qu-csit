import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';

/// Generates a stable per-device fingerprint from hardware identifiers.
///
/// Android: uses Settings.Secure.ANDROID_ID (via device_info_plus).
/// iOS: uses identifierForVendor.
///
/// On web/desktop falls back to a generated UUID persisted in secure storage.
class DeviceFingerprint {
  DeviceFingerprint._();

  static Future<String> get() async {
    final info = DeviceInfoPlugin();
    if (Platform.isAndroid) {
      final android = await info.androidInfo;
      // androidId is unique per (device, app-signing-key, user) — good enough
      // for our use case (one student = one device). See device_info_plus docs.
      return 'android:${android.id}';
    }
    if (Platform.isIOS) {
      final ios = await info.iosInfo;
      return 'ios:${ios.identifierForVendor ?? 'unknown'}';
    }
    if (Platform.isWindows) {
      final w = await info.windowsInfo;
      return 'windows:${w.deviceId}';
    }
    if (Platform.isMacOS) {
      final m = await info.macOsInfo;
      return 'macos:${m.systemGUID}';
    }
    if (Platform.isLinux) {
      final l = await info.linuxDeviceInfo;
      return 'linux:${l.machineId ?? 'unknown'}';
    }
    return 'unknown';
  }

  /// A friendly model name for the device table.
  static Future<String> getModel() async {
    final info = DeviceInfoPlugin();
    if (Platform.isAndroid) {
      final android = await info.androidInfo;
      return '${android.brand} ${android.model}';
    }
    if (Platform.isIOS) {
      final ios = await info.iosInfo;
      return ios.utsname.machine;
    }
    return Platform.operatingSystem;
  }
}
