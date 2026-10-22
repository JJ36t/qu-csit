import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/token_storage.dart';
import '../data/auth_api.dart';

/// Async auth state — holds the user profile when logged in, null when not.
class AuthState {
  const AuthState({
    this.me,
    this.isLoading = false,
    this.error,
    this.mustChangePassword = false,
  });

  final dynamic me; // AuthMeOut | null
  final bool isLoading;
  final String? error;
  final bool mustChangePassword;

  AuthState copyWith({
    dynamic me,
    bool? isLoading,
    String? error,
    bool? mustChangePassword,
    bool clearError = false,
    bool clearMustChange = false,
  }) {
    return AuthState(
      me: me ?? this.me,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      mustChangePassword:
          clearMustChange ? false : (mustChangePassword ?? this.mustChangePassword),
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._api, this._storage) : super(const AuthState());

  final AuthApi _api;
  final TokenStorage _storage;

  Future<void> login(String universityId, String password) async {
    state = const AuthState(isLoading: true);
    try {
      // Get device fingerprint lazily to avoid import cycle.
      final fp = await _readDeviceFingerprint();
      final model = await _readDeviceModel();
      final token = await _api.login(LoginRequest(
        universityId: universityId,
        password: password,
        deviceFingerprint: fp,
        deviceModel: model,
      ));
      await _storage.saveTokens(access: token.accessToken, refresh: token.refreshToken);
      await _storage.saveMustChangePassword(token.mustChangePassword);
      await _storage.saveUserRole(token.accessToken); // placeholder; real role comes from /me
      final me = await _api.me();
      await _storage.saveUserRole(me.user.role);
      await _storage.saveUserId(me.user.id);
      state = AuthState(
        me: me,
        mustChangePassword: token.mustChangePassword,
      );
    } on ApiError catch (e) {
      state = AuthState(error: e.messageAr);
    } catch (e) {
      state = AuthState(error: e.toString());
    }
  }

  Future<void> changePassword(String oldPwd, String newPwd) async {
    state = state.copyWith(isLoading: true);
    try {
      await _api.changePassword(ChangePasswordRequest(
        oldPassword: oldPwd,
        newPassword: newPwd,
      ));
      // Re-login not required — server invalidated refresh tokens but kept the
      // current access token valid until it expires.
      state = state.copyWith(isLoading: false, clearMustChange: true);
    } on ApiError catch (e) {
      state = state.copyWith(isLoading: false, error: e.messageAr);
      rethrow;
    }
  }

  Future<void> logout() async {
    final refresh = await _storage.getRefreshToken();
    try {
      await _api.logout(refresh);
    } catch (_) {
      // ignore — we're logging out anyway
    }
    await _storage.clear();
    state = const AuthState();
  }

  Future<void> loadFromStorage() async {
    final access = await _storage.getAccessToken();
    if (access == null || access.isEmpty) {
      state = const AuthState();
      return;
    }
    try {
      final me = await _api.me();
      final mustChange = await _storage.getMustChangePassword();
      state = AuthState(me: me, mustChangePassword: mustChange);
    } catch (_) {
      // Token expired AND refresh failed — log out.
      await _storage.clear();
      state = const AuthState();
    }
  }

  // Lazy import to avoid cycle.
  Future<String> _readDeviceFingerprint() async {
    return await _fingerprintFn();
  }

  Future<String> _readDeviceModel() async {
    return await _modelFn();
  }

  // Injected at app startup (see main.dart).
  static Future<String> Function() _fingerprintFn = () async => 'unknown';
  static Future<String> Function() _modelFn = () async => 'unknown';
  static void setDeviceFingerprintProviders(
    Future<String> Function() fp,
    Future<String> Function() model,
  ) {
    _fingerprintFn = fp;
    _modelFn = model;
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final api = ref.watch(authApiProvider);
  final storage = ref.watch(tokenStorageProvider);
  return AuthNotifier(api, storage);
});
