import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'app/router/app_router.dart';
import 'app/theme/app_theme.dart';
import 'core/device/device_fingerprint.dart';
import 'core/network/dio_client.dart';
import 'core/network/token_storage.dart';
import 'core/notifications/notification_service.dart';
import 'core/storage/local_db.dart';
import 'core/storage/providers.dart';
import 'features/announcements/data/announcements_api.dart';
import 'features/auth/data/auth_api.dart';
import 'features/auth/presentation/auth_provider.dart';
import 'l10n/gen/app_localizations.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.init();

  // Warm up device fingerprint cache (login will need it).
  DeviceFingerprint.get().catchError((_) => 'unknown');

  runApp(const ProviderScope(child: CsitApp()));
}

class CsitApp extends ConsumerWidget {
  const CsitApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Override core providers at the root.
    final secureStorage = FlutterSecureStorage(
      aOptions: const AndroidOptions(encryptedSharedPreferences: true),
    );
    final tokenStorage = TokenStorage(secureStorage);
    final dio = buildDio(tokenStorage: tokenStorage, secureStorage: secureStorage);
    final localDb = LocalDatabase();

    // Wire device fingerprint helpers into AuthNotifier.
    AuthNotifier.setDeviceFingerprintProviders(
      () => DeviceFingerprint.get(),
      () => DeviceFingerprint.getModel(),
    );

    return ProviderScope(
      overrides: [
        dioProvider.overrideWithValue(dio),
        tokenStorageProvider.overrideWithValue(tokenStorage),
        localDatabaseProvider.overrideWithValue(localDb),
        authApiProvider.overrideWithValue(AuthApi(dio)),
        announcementsApiProvider.overrideWithValue(AnnouncementsApi(dio)),
        notificationsApiProvider.overrideWithValue(NotificationsApi(dio)),
      ],
      child: const _MaterialApp(),
    );
  }
}

class _MaterialApp extends ConsumerStatefulWidget {
  const _MaterialApp();

  @override
  ConsumerState<_MaterialApp> createState() => _MaterialAppState();
}

class _MaterialAppState extends ConsumerState<_MaterialApp> {
  bool _authLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadAuth();
  }

  Future<void> _loadAuth() async {
    await ref.read(authProvider.notifier).loadFromStorage();
    if (mounted) setState(() => _authLoaded = true);
  }

  @override
  Widget build(BuildContext context) {
    if (!_authLoaded) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        home: const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
      );
    }
    final router = buildRouter(ref);
    return MaterialApp.router(
      title: 'كلية علوم الحاسوب – القادسية',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.light,
      locale: const Locale('ar'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => Directionality(
        textDirection: TextDirection.rtl,
        child: child ?? const SizedBox.shrink(),
      ),
      routerConfig: router,
    );
  }
}
