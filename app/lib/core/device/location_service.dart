import 'package:geolocator/geolocator.dart';

/// Wraps Geolocator with permission handling. Used for attendance scan only —
/// we never track in the background (privacy brief §11).
class LocationService {
  LocationService._();

  /// Returns the current GPS position, or null if denied/disabled.
  ///
  /// Will request permission if not yet granted. Returns null gracefully if
  /// the user denies — caller should still send the scan with `lat: null`,
  /// and the server marks it `flagged` for review (never rejected).
  static Future<({double lat, double lng, double accuracyM})?> getCurrent() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return null;

    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.denied ||
        perm == LocationPermission.deniedForever) {
      return null;
    }
    final pos = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.medium,
        timeLimit: Duration(seconds: 5),
      ),
    );
    return (
      lat: pos.latitude,
      lng: pos.longitude,
      accuracyM: pos.accuracy,
    );
  }
}
