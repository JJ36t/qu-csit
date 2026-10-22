import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists access/refresh tokens in platform keystore (Keystore/Keychain).
class TokenStorage {
  TokenStorage(this._storage);

  final FlutterSecureStorage _storage;

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _kRole = 'user_role';
  static const _kUserId = 'user_id';
  static const _kMustChangePassword = 'must_change_password';

  Future<String?> getAccessToken() => _storage.read(key: _kAccess);
  Future<String?> getRefreshToken() => _storage.read(key: _kRefresh);

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<void> saveUserRole(String role) => _storage.write(key: _kRole, value: role);
  Future<String?> getUserRole() => _storage.read(key: _kRole);

  Future<void> saveUserId(String id) => _storage.write(key: _kUserId, value: id);
  Future<String?> getUserId() => _storage.read(key: _kUserId);

  Future<void> saveMustChangePassword(bool v) =>
      _storage.write(key: _kMustChangePassword, value: v.toString());
  Future<bool> getMustChangePassword() async =>
      (await _storage.read(key: _kMustChangePassword)) == 'true';

  Future<void> clear() async {
    await _storage.deleteAll();
  }
}
