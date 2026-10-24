import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/arabic_formatting.dart';
import '../../announcements/data/announcements_repository.dart' show localDatabaseProvider;
import '../data/materials_api.dart';

/// Stub for the "Materials" tab — placeholder while we wait for Phase 3+ to
/// wire the user's enrolled offerings. Phase 6 will make this a full list.
class MaterialsTab extends ConsumerStatefulWidget {
  const MaterialsTab({super.key});

  @override
  ConsumerState<MaterialsTab> createState() => _MaterialsTabState();
}

class _MaterialsTabState extends ConsumerState<MaterialsTab> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('المواد')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.folder_outlined, size: 64, color: Theme.of(context).colorScheme.primary.withOpacity(0.5)),
              const SizedBox(height: 16),
              Text(
                'قائمة المواد',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'هنا ستجد محاضراتك (PDF) وروابط الفيديو مرتبة حسب الأسبوع.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.refresh),
                label: const Text('تحديث'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
