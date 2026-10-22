import 'package:csit_app/shared/models/auth_models.dart';
import 'package:csit_app/shared/models/timetable_models.dart';
import 'package:csit_app/shared/models/comms_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Auth models', () {
    test('TokenPair parses login response', () {
      final json = {
        'access_token': 'abc.def.ghi',
        'refresh_token': 'ref.token.here',
        'expires_in': 900,
        'token_type': 'Bearer',
        'must_change_password': true,
      };
      final t = TokenPair.fromJson(json);
      expect(t.accessToken, 'abc.def.ghi');
      expect(t.refreshToken, 'ref.token.here');
      expect(t.expiresInSeconds, 900);
      expect(t.mustChangePassword, true);
    });

    test('AuthMeOut parses nested user/student/staff', () {
      final json = {
        'user': {
          'id': 'u-1',
          'role': 'student',
          'university_id': 'S1001',
          'full_name_ar': 'طالب 1',
          'email': 's1@example.com',
          'phone': '0780123456',
          'status': 'active',
          'must_change_password': true,
          'last_login_at': '2026-10-23T08:00:00Z',
        },
        'student': {
          'user_id': 'u-1',
          'department_id': 'd-1',
          'stage': 2,
          'study_type': 'morning',
          'group_id': 'g-1',
          'enrollment_year': 2025,
          'status': 'active',
        },
        'staff': null,
      };
      final me = AuthMeOut.fromJson(json);
      expect(me.user.fullNameAr, 'طالب 1');
      expect(me.user.role, 'student');
      expect(me.student!.stage, 2);
      expect(me.staff, isNull);
    });
  });

  group('Timetable models', () {
    test('TimetableSlotOut parses weekday + times', () {
      final json = {
        'id': 'slot-1',
        'offering_id': 'off-1',
        'weekday': 0,
        'start_time': '09:00:00',
        'end_time': '10:30:00',
        'room_id': 'room-1',
        'kind': 'theory',
      };
      final s = TimetableSlotOut.fromJson(json);
      expect(s.weekday, 0); // Sunday
      expect(s.startTime, '09:00:00');
      expect(s.kind, 'theory');
    });

    test('TimetableEntry parses effective_start + is_cancelled', () {
      final json = {
        'slot': {
          'id': 'slot-1',
          'offering_id': 'off-1',
          'weekday': 0,
          'start_time': '09:00:00',
          'end_time': '10:30:00',
          'room_id': null,
          'kind': 'theory',
        },
        'changes': [],
        'effective_start': '11:00:00',
        'effective_end': '12:30:00',
        'effective_room_id': 'room-2',
        'is_cancelled': false,
      };
      final e = TimetableEntry.fromJson(json);
      expect(e.effectiveStart, '11:00:00');
      expect(e.isCancelled, false);
    });

    test('TimetableDay groups entries under a date', () {
      final json = {
        'date': '2026-10-25',
        'entries': [],
      };
      final d = TimetableDay.fromJson(json);
      expect(d.date, '2026-10-25');
      expect(d.entries, isEmpty);
    });
  });

  group('Comms models', () {
    test('AnnouncementOut parses pinned + is_read', () {
      final json = {
        'id': 'a-1',
        'scope': 'college',
        'scope_id': null,
        'title': 'إعلان الكلية',
        'body': 'محتوى الإعلان',
        'priority': 1,
        'pinned': true,
        'publish_at': null,
        'expires_at': null,
        'created_at': '2026-10-23T08:00:00Z',
        'created_by': 'u-2',
        'is_read': false,
      };
      final a = AnnouncementOut.fromJson(json);
      expect(a.pinned, true);
      expect(a.isRead, false);
      expect(a.title, 'إعلان الكلية');
    });

    test('NotificationList parses items + total + unread', () {
      final json = {
        'items': [
          {
            'id': 'n-1',
            'type': 'announcement',
            'title': 'تنبيه',
            'body': 'إعلان جديد',
            'data': {'announcement_id': 'a-1'},
            'read_at': null,
            'created_at': '2026-10-23T08:00:00Z',
          }
        ],
        'total': 1,
        'unread': 1,
      };
      final l = NotificationList.fromJson(json);
      expect(l.items.length, 1);
      expect(l.total, 1);
      expect(l.unread, 1);
      expect(l.items.first.title, 'تنبيه');
    });
  });
}

// Note: attendance models live in features/attendance/data/session_models.dart
// and require the same build_runner codegen. Tests for those land once the
// Flutter SDK is available on the host.
