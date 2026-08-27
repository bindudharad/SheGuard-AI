import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/incident.dart';
import '../providers/auth_provider.dart';
import '../providers/contact_provider.dart';
import '../providers/incident_provider.dart';
import '../services/api_service.dart';
import '../services/emergency_call_service.dart';
import '../services/notification_service.dart';
import '../core/app_theme.dart';
import '../widgets/empty_state.dart';
import '../widgets/premium_ui.dart';

class IncidentHistoryScreen extends StatefulWidget {
  const IncidentHistoryScreen({super.key});

  static const route = '/incident-history';

  @override
  State<IncidentHistoryScreen> createState() => _IncidentHistoryScreenState();
}

class _IncidentHistoryScreenState extends State<IncidentHistoryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<IncidentProvider>();
      provider.loadIncidentFeed();
      provider.startIncidentRealtime();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<IncidentProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final incident =
          context.read<IncidentProvider>().pendingEmergencyIncident;
      if (incident != null) {
        _showEmergencyPopup(context, incident);
      }
    });
    return PremiumScaffold(
      appBar: AppBar(title: const Text('Incident Feed')),
      child: RefreshIndicator(
        onRefresh: () => provider.loadIncidentFeed(),
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            GlassCard(
              glowColor: AppTheme.emergency,
              child: Row(
                children: [
                  const GlowIcon(
                    icon: Icons.sensors,
                    color: AppTheme.emergency,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Realtime Detection Feed',
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          provider.realtimeConnected
                              ? 'Live sync active. New AI incidents appear instantly.'
                              : 'Showing stored incidents. Pull to refresh.',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: .68),
                          ),
                        ),
                      ],
                    ),
                  ),
                  _LiveBadge(active: provider.realtimeConnected),
                ],
              ),
            ),
            const SizedBox(height: 18),
            if (provider.loading) ...[
              const ShimmerBar(height: 14),
              const SizedBox(height: 12),
              const ShimmerBar(width: 210, height: 14),
              const SizedBox(height: 18),
            ],
            if (provider.liveIncidents.isEmpty && !provider.loading)
              const EmptyState(
                icon: Icons.warning_amber,
                title: 'No AI incidents yet',
                message:
                    'Emergency detections and CCTV evidence will appear here as soon as the backend stores them.',
              ),
            ...provider.liveIncidents.map(
              (incident) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: IncidentCard(incident: incident),
              ),
            ),
            if (provider.error != null)
              Text(
                provider.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _showEmergencyPopup(
    BuildContext context,
    Incident incident,
  ) async {
    context.read<IncidentProvider>().emergencyPopupHandled(incident);
    final contactProvider = context.read<ContactProvider>();
    final callService = context.read<EmergencyCallService>();
    final notifications = context.read<NotificationService>();
    final user = context.read<AuthProvider>().user;
    if (contactProvider.contacts.isEmpty && user != null) {
      await contactProvider.load(user.userId);
    }
    await notifications.vibrateOnce(_incidentCallKey(incident));
    await callService.dialFirstParentOnce(
      contactProvider.visibleContacts,
      incidentKey: _incidentCallKey(incident),
    );
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('🚨 Emergency Detected'),
          content: Text(
            '${_title(incident.incidentType)} detected with '
            '${_confidencePercent(incident)}% confidence.\n\n'
            'Calling saved parent number...',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Dismiss'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => IncidentDetailScreen(incident: incident),
                  ),
                );
              },
              child: const Text('Open details'),
            ),
          ],
        );
      },
    );
  }
}

class IncidentCard extends StatelessWidget {
  const IncidentCard({super.key, required this.incident});

  final Incident incident;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => IncidentDetailScreen(incident: incident),
        ),
      ),
      child: GlassCard(
        glowColor: AppTheme.emergency,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: SizedBox(
                height: 168,
                width: double.infinity,
                child: _NetworkImagePreview(
                  path: incident.thumbnailReference,
                ),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: Text(
                    _title(incident.incidentType),
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                  ),
                ),
                _StatusPill(status: incident.status ?? 'new'),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _InfoChip(
                  icon: Icons.percent,
                  label: '${_confidencePercent(incident)}%',
                ),
                _InfoChip(
                  icon: Icons.schedule,
                  label: _friendlyTime(incident.createdAt),
                ),
                _InfoChip(
                  icon: Icons.location_on,
                  label: _locationLabel(incident),
                ),
                if (incident.incidentFolderId != null)
                  _InfoChip(
                    icon: Icons.folder,
                    label: incident.incidentFolderId!,
                  ),
                if (incident.riskScore != null)
                  _InfoChip(
                    icon: Icons.shield,
                    label: 'Risk ${incident.riskScore!.toInt()}/100',
                  ),
                if (incident.followingRelationship != null)
                  _InfoChip(
                    icon: Icons.follow_the_signs,
                    label: 'Following Detected',
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _VideoButton(
                    path: incident.videoReference,
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filledTonal(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => IncidentDetailScreen(incident: incident),
                    ),
                  ),
                  icon: const Icon(Icons.chevron_right),
                  tooltip: 'Open details',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class IncidentDetailScreen extends StatelessWidget {
  const IncidentDetailScreen({super.key, required this.incident});

  final Incident incident;

  @override
  Widget build(BuildContext context) {
    return PremiumScaffold(
      appBar: AppBar(title: const Text('Incident Details')),
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          GlassCard(
            glowColor: AppTheme.emergency,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: SizedBox(
                    height: 240,
                    width: double.infinity,
                    child: _NetworkImagePreview(
                      path: incident.thumbnailReference,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  _title(incident.incidentType),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 12),
                _DetailRow('Confidence', '${_confidencePercent(incident)}%'),
                _DetailRow('Timestamp', _fullTime(incident.createdAt)),
                _DetailRow('Location', _locationLabel(incident)),
                _DetailRow('Status', incident.status ?? 'new'),
                if (incident.cameraId != null)
                  _DetailRow('Camera', incident.cameraId!),
                if (incident.incidentFolderId != null)
                  _DetailRow(
                    'Storage folder',
                    '/uploads/incidents/${incident.incidentFolderId}/',
                  ),
                if (incident.aiSummary != null)
                  _DetailRow('Summary', incident.aiSummary!),
                if (incident.explanation != null)
                  _DetailRow('AI explanation', incident.explanation!),
                if (incident.riskScore != null)
                  _DetailRow('Threat Risk', '${incident.riskScore!.toInt()}/100'),
                if (incident.riskLevel != null)
                  _DetailRow('Risk Level', incident.riskLevel!),
                const SizedBox(height: 16),
                _VideoButton(
                  path: incident.videoReference,
                  label: 'Open Emergency Video',
                ),
                const SizedBox(height: 16),
                _MetadataPanel(path: incident.metadataReference),
                // Phase G: Behavior / Risk info
                if (incident.followingRelationship != null)
                  _FollowingPanel(following: incident.followingRelationship!),
                if (incident.behaviors.isNotEmpty)
                  _BehaviorsPanel(behaviors: incident.behaviors),
                if (incident.x402Metadata != null)
                  _X402Panel(x402: incident.x402Metadata!),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FollowingPanel extends StatelessWidget {
  const _FollowingPanel({required this.following});

  final Map<String, dynamic> following;

  @override
  Widget build(BuildContext context) {
    final targetId = following['target_id']?.toString() ?? '?';
    final followerId = following['follower_id']?.toString() ?? '?';
    final score = (following['score'] as num?)?.toDouble() ?? 0.0;
    final duration = (following['duration_seconds'] as num?)?.toDouble() ?? 0.0;
    final distance = (following['distance_meters'] as num?)?.toDouble() ?? 0.0;
    final trend = following['distance_trend']?.toString() ?? 'unknown';
    final directionSim = (following['direction_similarity'] as num?)?.toDouble() ?? 0.0;
    final trajectorySim = (following['trajectory_similarity'] as num?)?.toDouble() ?? 0.0;
    final turnSim = (following['turn_match_score'] as num?)?.toDouble() ?? 0.0;

    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.amber.withValues(alpha: .1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.withValues(alpha: .3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '⚠ SUSPICIOUS FOLLOWING DETECTED',
            style: TextStyle(
              color: Colors.amber,
              fontWeight: FontWeight.w900,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 10),
          _DetailRow('Target', 'Track #$targetId'),
          _DetailRow('Follower', 'Track #$followerId'),
          _DetailRow('Following Score', '${score.toInt()}%'),
          _DetailRow('Duration', '${duration.toStringAsFixed(1)}s'),
          _DetailRow('Distance', '${distance.toStringAsFixed(1)}m'),
          _DetailRow('Distance Trend', trend.toUpperCase()),
          _DetailRow('Direction Match', '${(directionSim * 100).toInt()}%'),
          _DetailRow('Trajectory Match', '${(trajectorySim * 100).toInt()}%'),
          _DetailRow('Turn Match', '${(turnSim * 100).toInt()}%'),
          if (incidentRisk != null)
            _DetailRow('Threat Risk', '${incidentRisk!.toInt()}/100'),
        ],
      ),
    );
  }

  double? get incidentRisk => null;
}

class _BehaviorsPanel extends StatelessWidget {
  const _BehaviorsPanel({required this.behaviors});

  final List<dynamic> behaviors;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: .12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Detected Behaviors',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 8),
          ...behaviors.map((b) {
            final map = b is Map ? b : {};
            final behavior = map['behavior']?.toString() ?? 'unknown';
            final score = (map['score'] as num?)?.toDouble() ?? 0.0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Expanded(child: Text(behavior, style: const TextStyle(color: Colors.white70))),
                  Text(
                    '${score.toInt()}%',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _X402Panel extends StatelessWidget {
  const _X402Panel({required this.x402});

  final Map<String, dynamic> x402;

  @override
  Widget build(BuildContext context) {
    final service = x402['service']?.toString() ?? 'safety-intelligence';
    final amount = (x402['amount'] as num?)?.toDouble() ?? 0.0;
    final currency = x402['currency']?.toString() ?? 'ALGO';
    final network = x402['network']?.toString() ?? 'testnet';
    final state = x402['state']?.toString() ?? 'UNKNOWN';
    final txId = x402['transaction_id']?.toString() ?? 'N/A';

    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.purple.withValues(alpha: .1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.purple.withValues(alpha: .3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'x402 Payment / Intelligence',
            style: TextStyle(
              color: Colors.purple,
              fontWeight: FontWeight.w900,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 8),
          _DetailRow('Service', service),
          _DetailRow('Amount', '$amount $currency'),
          _DetailRow('Network', network),
          _DetailRow('Status', state),
          _DetailRow('Transaction ID', txId),
          if (x402['intelligence_result'] != null)
            _DetailRow('Intelligence', 'Available'),
        ],
      ),
    );
  }
}

class _MetadataPanel extends StatelessWidget {
  const _MetadataPanel({required this.path});

  final String? path;

  @override
  Widget build(BuildContext context) {
    if (path == null) return const SizedBox.shrink();
    return FutureBuilder<Map<String, dynamic>?>(
      future: context.read<ApiService>().publicJson(path),
      builder: (context, snapshot) {
        final metadata = snapshot.data;
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const ShimmerBar(height: 12);
        }
        if (metadata == null) {
          return const _DetailRow('Metadata', 'No metadata file available');
        }
        final capture = metadata['capture'] as Map<String, dynamic>?;
        final media = metadata['media'] as Map<String, dynamic>?;
        final type = metadata['incident_type']?.toString() ??
            capture?['incident_type']?.toString();
        final confidence = metadata['confidence']?.toString() ??
            capture?['confidence']?.toString();
        final files = metadata['files'] as Map<String, dynamic>?;
        final frames = files?['frames'] as List?;
        final frameCount = metadata['frame_count']?.toString() ??
            media?['frame_count']?.toString() ??
            frames?.length.toString();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _DetailRow('Metadata file', 'Loaded from metadata.json'),
            if (type != null) _DetailRow('Metadata type', _title(type)),
            if (confidence != null)
              _DetailRow('Metadata confidence', confidence),
            if (frameCount != null) _DetailRow('Frame count', frameCount),
          ],
        );
      },
    );
  }
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color:
            (active ? Colors.greenAccent : Colors.white).withValues(alpha: .14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: active ? Colors.greenAccent : Colors.white38,
        ),
      ),
      child: Text(
        active ? 'LIVE' : 'OFFLINE',
        style: TextStyle(
          color: active ? Colors.greenAccent : Colors.white70,
          fontWeight: FontWeight.w900,
          fontSize: 11,
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.emergency.withValues(alpha: .16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        status.toUpperCase(),
        style: const TextStyle(
          color: AppTheme.emergency,
          fontWeight: FontWeight.w900,
          fontSize: 11,
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: Colors.white70),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: .58),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _NoMediaPreview extends StatelessWidget {
  const _NoMediaPreview();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black.withValues(alpha: .22),
      child: const Center(
        child: Icon(Icons.image_not_supported, color: Colors.white54, size: 42),
      ),
    );
  }
}

class _NetworkImagePreview extends StatelessWidget {
  const _NetworkImagePreview({required this.path});

  final String? path;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: context.read<ApiService>().publicMediaUrl(path),
      builder: (context, snapshot) {
        final url = snapshot.data;
        if (url == null) return const _NoMediaPreview();
        return Image.network(
          url,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => const _NoMediaPreview(),
        );
      },
    );
  }
}

class _VideoButton extends StatelessWidget {
  const _VideoButton({required this.path, this.label = 'Video Preview'});

  final String? path;
  final String label;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: context.read<ApiService>().publicMediaUrl(path),
      builder: (context, snapshot) {
        final url = snapshot.data;
        return FilledButton.icon(
          onPressed: url == null
              ? null
              : () => launchUrl(
                    Uri.parse(url),
                    mode: LaunchMode.externalApplication,
                  ),
          icon: const Icon(Icons.play_circle),
          label: Text(label),
        );
      },
    );
  }
}

String _title(String value) {
  return value
      .split(RegExp(r'[_\-\s]+'))
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}

int _confidencePercent(Incident incident) {
  return (incident.confidence * 100).clamp(0, 100).round();
}

String _locationLabel(Incident incident) {
  final lat = incident.latitude;
  final lng = incident.longitude;
  if (lat == null || lng == null) return 'Location unavailable';
  return '${lat.toStringAsFixed(5)}, ${lng.toStringAsFixed(5)}';
}

String _friendlyTime(DateTime? time) {
  if (time == null) return 'Time unavailable';
  final diff = DateTime.now().difference(time.toLocal());
  if (diff.inMinutes < 1) return 'Just now';
  if (diff.inHours < 1) return '${diff.inMinutes} min ago';
  if (diff.inDays < 1) return '${diff.inHours} hr ago';
  if (diff.inDays == 1) return 'Yesterday';
  return '${time.toLocal().day}/${time.toLocal().month}/${time.toLocal().year}';
}

String _fullTime(DateTime? time) {
  if (time == null) return 'Time unavailable';
  final local = time.toLocal();
  final minute = local.minute.toString().padLeft(2, '0');
  return '${local.day}/${local.month}/${local.year} ${local.hour}:$minute';
}

String _incidentCallKey(Incident incident) {
  return 'incident-${incident.incidentId ?? incident.createdAt?.millisecondsSinceEpoch ?? incident.hashCode}';
}
