import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../announcements/presentation/announcements_list_screen.dart';
import '../../auth/presentation/auth_provider.dart';
import '../../notifications/presentation/notifications_tab.dart';
import '../../timetable/presentation/timetable_tab.dart';
import 'home_tab.dart';

/// Bottom-nav shell — two flavors by role:
/// - student: Home · Timetable · **Scan** (center FAB) · Materials · More
/// - instructor: Home · My schedule · **Start attendance** (center FAB) · My courses · More
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final isStudent = auth.me?.user.role == 'student';
    final isInstructor = auth.me?.user.role == 'instructor';

    final destinations = <NavigationDestination>[
      const NavigationDestination(
        icon: Icon(Icons.home_outlined),
        selectedIcon: Icon(Icons.home_rounded),
        label: 'الرئيسية',
      ),
      const NavigationDestination(
        icon: Icon(Icons.calendar_view_day_outlined),
        selectedIcon: Icon(Icons.calendar_view_day_rounded),
        label: 'الجدول',
      ),
      // Scan / Start attendance — handled by the FAB, not a real destination
      const NavigationDestination(
        icon: Icon(Icons.qr_code_scanner_rounded, color: Colors.transparent),
        selectedIcon: Icon(Icons.qr_code_scanner_rounded, color: Colors.transparent),
        label: '',
      ),
      NavigationDestination(
        icon: const Icon(Icons.book_outlined),
        selectedIcon: const Icon(Icons.book_rounded),
        label: isInstructor ? 'موادي' : 'المواد',
      ),
      const NavigationDestination(
        icon: Icon(Icons.more_horiz_outlined),
        selectedIcon: Icon(Icons.more_horiz_rounded),
        label: 'المزيد',
      ),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _index == 2 ? 0 : _index, // FAB = action, not navigation
        children: const [
          HomeTab(),
          TimetableTab(),
          SizedBox.shrink(), // FAB target — replaced below
          AnnouncementsListScreen(),
          NotificationsTab(),
        ],
      ),
      floatingActionButton: FloatingActionButton.large(
        heroTag: 'scan_fab',
        onPressed: () {
          // Phase 4 — opens the QR scanner.
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('المسح متاح في المرحلة 4')),
          );
        },
        child: Icon(
          isStudent ? Icons.qr_code_scanner_rounded : Icons.play_arrow_rounded,
          size: 36,
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: destinations,
        backgroundColor: Theme.of(context).colorScheme.surface,
        indicatorColor: Theme.of(context).colorScheme.primaryContainer,
        labelTextStyle: WidgetStateProperty.all(
          Theme.of(context).textTheme.labelSmall,
        ),
      ),
    );
  }
}
