import 'package:flutter/material.dart';

import '../models/incident.dart';

class TimelineCard extends StatelessWidget {
  const TimelineCard({
    super.key,
    required this.incident,
    required this.onExpand,
  });

  final Incident incident;
  final Future<void> Function() onExpand;

  @override
  Widget build(BuildContext context) {
    final title =
        incident.incidentType.contains('sos') ? 'Help alert' : 'Safety alert';
    return Card(
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: Colors.red.shade100,
          child: const Icon(Icons.warning, color: Colors.red),
        ),
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          incident.createdAt == null
              ? 'Time unavailable'
              : _friendlyTime(incident.createdAt!),
        ),
        onExpansionChanged: (open) {
          if (open) onExpand();
        },
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(incident.aiSummary ?? 'No incident summary available.'),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              incident.evidence.isEmpty
                  ? 'Evidence: none linked yet'
                  : 'Evidence files: ${incident.evidence.length}',
              style: Theme.of(context).textTheme.labelLarge,
            ),
          ),
        ],
      ),
    );
  }
}

String _friendlyTime(DateTime time) {
  final now = DateTime.now();
  final difference = now.difference(time);
  if (difference.inMinutes < 1) return 'Just now';
  if (difference.inHours < 1) return '${difference.inMinutes} minutes ago';
  if (difference.inDays < 1) return '${difference.inHours} hours ago';
  if (difference.inDays == 1) return 'Yesterday';
  return '${time.day}/${time.month}/${time.year}';
}
