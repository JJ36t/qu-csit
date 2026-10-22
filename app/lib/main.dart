import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'app/theme/app_theme.dart';
import 'l10n/gen/app_localizations.dart';

void main() {
  runApp(const ProviderScope(child: CsitApp()));
}

class CsitApp extends StatelessWidget {
  const CsitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'كلية علوم الحاسوب – القادسية',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.light,
      // Arabic first, English fallback later.
      locale: const Locale('ar'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) {
        // Force RTL layout regardless of system locale (brief §1 rule 4).
        return Directionality(
          textDirection: TextDirection.rtl,
          child: child!,
        );
      },
      home: const Scaffold(
        body: Center(child: Text('المرحلة 0 — هيكلة المشروع جاهزة')),
      ),
    );
  }
}
