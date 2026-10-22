import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../../core/device/device_fingerprint.dart';
import '../../../core/device/location_service.dart';
import '../../../core/network/dio_client.dart';
import '../data/attendance_api.dart';

/// Student-facing QR scanner screen.
///
/// Uses mobile_scanner to read the instructor's rotating QR. On a successful
/// read, posts {session_id, token, device_id, location} to /attendance/scan
/// and shows the Arabic result.
class StudentScannerScreen extends ConsumerStatefulWidget {
  const StudentScannerScreen({super.key});

  @override
  ConsumerState<StudentScannerScreen> createState() => _StudentScannerScreenState();
}

class _StudentScannerScreenState extends ConsumerState<StudentScannerScreen> {
  MobileScannerController? _controller;
  bool _processing = false;
  String? _resultMessage;
  Color? _resultColor;
  bool _torchOn = false;
  bool _scanning = true;

  @override
  void initState() {
    super.initState();
    _controller = MobileScannerController(
      detectionSpeed: DetectionSpeed.noDuplicates,
      facing: CameraFacing.back,
      torchEnabled: false,
    );
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _handleScan(String rawValue) async {
    if (_processing || !_scanning) return;
    setState(() {
      _processing = true;
      _scanning = false;
      _resultMessage = 'جارٍ التحقق…';
      _resultColor = Colors.grey;
    });

    try {
      // Parse the QR payload: `session_id|window_index|sig`
      final parts = rawValue.split('|');
      if (parts.length != 3) {
        setState(() {
          _resultMessage = 'رمز غير صالح';
          _resultColor = Colors.red;
        });
        return;
      }
      final sessionId = parts[0];

      // Get device fingerprint (matches what was sent at login → bound device)
      final fp = await DeviceFingerprint.get();

      // Get current location (returns null on denial — server marks flagged)
      final loc = await LocationService.getCurrent();

      final api = ref.read(attendanceApiProvider);
      final response = await api.scan(
        sessionId: sessionId,
        token: rawValue,
        deviceFingerprint: fp,
        location: loc != null
            ? {'lat': loc.lat, 'lng': loc.lng, 'accuracy_m': loc.accuracyM}
            : null,
      );

      setState(() {
        _resultMessage = response.messageAr;
        _resultColor = response.flagged ? Colors.orange : Colors.green;
      });
    } on ApiError catch (e) {
      setState(() {
        _resultMessage = e.messageAr;
        _resultColor = Colors.red;
      });
    } catch (e) {
      setState(() {
        _resultMessage = 'خطأ غير متوقع: $e';
        _resultColor = Colors.red;
      });
    } finally {
      if (mounted) {
        setState(() => _processing = false);
      }
    }
  }

  void _reset() {
    setState(() {
      _scanning = true;
      _resultMessage = null;
      _resultColor = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مسح الحضور'),
        actions: [
          IconButton(
            icon: Icon(_torchOn ? Icons.flash_on : Icons.flash_off),
            onPressed: () {
              _controller?.toggleTorch();
              setState(() => _torchOn = !_torchOn);
            },
          ),
          IconButton(
            icon: const Icon(Icons.cameraswitch),
            onPressed: () => _controller?.switchCamera(),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Camera preview
          MobileScanner(
            controller: _controller!,
            onDetect: (capture) {
              final barcodes = capture.barcodes;
              for (final bc in barcodes) {
                if (bc.rawValue != null) {
                  _handleScan(bc.rawValue!);
                  break;
                }
              }
            },
          ),

          // Scan overlay frame (RTL)
          _ScanOverlay(),

          // Result card at the bottom
          if (_resultMessage != null)
            Positioned(
              left: 16,
              right: 16,
              bottom: 32,
              child: Card(
                color: _resultColor,
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        _resultColor == Colors.green
                            ? Icons.check_circle
                            : _resultColor == Colors.orange
                                ? Icons.warning
                                : Icons.error,
                        color: Colors.white,
                        size: 48,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _resultMessage!,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      if (!_processing) ...[
                        const SizedBox(height: 16),
                        FilledButton(
                          onPressed: _reset,
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: _resultColor,
                          ),
                          child: const Text('مسح مرة أخرى'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ScanOverlay extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ColorFiltered(
      colorFilter: ColorFilter.mode(
        Colors.black.withOpacity(0.4),
        BlendMode.srcOut,
      ),
      child: Stack(
        children: [
          Center(
            child: Container(
              height: 250,
              width: 250,
              decoration: BoxDecoration(
                color: Colors.red, // this color is filtered out → transparent
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
