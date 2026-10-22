import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/auth_provider.dart';
import '../features/auth/presentation/change_password_screen.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/home/presentation/home_shell.dart';
import 'routes.dart';

/// go_router with role-based guards.
///
/// - If no token in storage → /login.
/// - If token exists but must_change_password → /change-password.
/// - Otherwise → /home (the shell with bottom nav).
GoRouter buildRouter(WidgetRef ref) {
  final auth = ref.watch(authProvider);

  return GoRouter(
    initialLocation: Routes.home,
    redirect: (context, state) {
      final loggedIn = auth.me != null;
      final mustChange = auth.mustChangePassword;
      final isLogin = state.matchedLocation == Routes.login;
      final isChangePw = state.matchedLocation == Routes.changePassword;

      if (!loggedIn && !isLogin) return Routes.login;
      if (loggedIn && mustChange && !isChangePw) return Routes.changePassword;
      if (loggedIn && !mustChange && (isLogin || isChangePw)) return Routes.home;
      return null;
    },
    refreshListenable: _AuthListenable(ref),
    routes: [
      GoRoute(
        path: Routes.login,
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: Routes.changePassword,
        builder: (_, __) => const ChangePasswordScreen(),
      ),
      GoRoute(
        path: Routes.home,
        builder: (_, __) => const HomeShell(),
      ),
    ],
  );
}

/// Bridges AuthState changes into a Listenable for go_router's refreshListenable.
class _AuthListenable extends ChangeNotifier {
  _AuthListenable(WidgetRef ref) {
    ref.listen<AuthState>(authProvider, (_, __) => notifyListeners());
  }
}
