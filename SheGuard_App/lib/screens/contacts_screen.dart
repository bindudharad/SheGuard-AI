import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/emergency_contact.dart';
import '../providers/auth_provider.dart';
import '../providers/contact_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/premium_ui.dart';
import '../core/app_theme.dart';

class ContactsScreen extends StatefulWidget {
  const ContactsScreen({super.key});

  static const route = '/contacts';

  @override
  State<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends State<ContactsScreen> {
  final _name = TextEditingController();
  final _relation = TextEditingController();
  final _phone = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final user = context.read<AuthProvider>().user;
      if (user != null) context.read<ContactProvider>().load(user.userId);
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _relation.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final user = context.read<AuthProvider>().user;
    final contactProvider = context.read<ContactProvider>();
    if (user == null) return;
    if (_name.text.trim().length < 2 || _phone.text.trim().length < 7) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Enter a valid contact name and phone number.')),
      );
      return;
    }
    final ok = await contactProvider.add(
      EmergencyContact(
        userId: user.userId,
        contactName: _name.text.trim(),
        relation: _relation.text.trim().isEmpty
            ? 'Trusted contact'
            : _relation.text.trim(),
        phoneNumber: _phone.text.trim(),
      ),
    );
    if (!mounted) return;
    if (ok) {
      _name.clear();
      _relation.clear();
      _phone.clear();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(contactProvider.error ?? 'Could not save contact.')),
      );
    }
  }

  Future<void> _edit(EmergencyContact contact) async {
    _name.text = contact.displayName;
    _relation.text = contact.displayRelation;
    _phone.text = contact.displayPhoneNumber;
    final contactProvider = context.read<ContactProvider>();
    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit local contact'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 10),
            TextField(
                controller: _relation,
                decoration: const InputDecoration(labelText: 'Relation')),
            const SizedBox(height: 10),
            TextField(
                controller: _phone,
                decoration: const InputDecoration(labelText: 'Phone')),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Save')),
        ],
      ),
    );
    if (save == true && mounted) {
      await contactProvider.editLocal(
        contact,
        name: _name.text.trim(),
        relation: _relation.text.trim(),
        phoneNumber: _phone.text.trim(),
      );
    }
    _name.clear();
    _relation.clear();
    _phone.clear();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ContactProvider>();
    final contacts = provider.visibleContacts;
    return PremiumScaffold(
      appBar: AppBar(title: const Text('Emergency Contacts')),
      child: RefreshIndicator(
        onRefresh: () async {
          final user = context.read<AuthProvider>().user;
          final contactProvider = context.read<ContactProvider>();
          if (user != null) await contactProvider.load(user.userId);
        },
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            GlassCard(
              glowColor: AppTheme.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Trusted Circle',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Add the people SheGuard should reach first when every second matters.',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: .7),
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    controller: _name,
                    decoration: const InputDecoration(
                        labelText: 'Contact name',
                        prefixIcon: Icon(Icons.person)),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _relation,
                    decoration: const InputDecoration(
                        labelText: 'Relationship',
                        prefixIcon: Icon(Icons.group)),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _phone,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(
                        labelText: 'Phone number',
                        prefixIcon: Icon(Icons.phone)),
                  ),
                  const SizedBox(height: 14),
                  ElevatedButton.icon(
                    onPressed: provider.loading ? null : _add,
                    icon: const Icon(Icons.add_call),
                    label: const Text('Add trusted contact'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            if (provider.loading) ...[
              const ShimmerBar(height: 14),
              const SizedBox(height: 12),
              const ShimmerBar(width: 220, height: 14),
            ],
            if (contacts.isEmpty && !provider.loading)
              const EmptyState(
                icon: Icons.contact_emergency,
                title: 'No contacts yet',
                message:
                    'Add a trusted person who can be reached during emergencies.',
              ),
            ...contacts.map(
              (contact) => Dismissible(
                key: ValueKey(contact.contactId),
                direction: DismissDirection.endToStart,
                background: Container(
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 20),
                  decoration: BoxDecoration(
                    color: AppTheme.emergency.withValues(alpha: .25),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                onDismissed: (_) => provider.removeLocal(contact.contactId),
                child: PremiumListTile(
                  icon: contact.isFavorite ? Icons.star : Icons.person,
                  color: contact.isFavorite ? AppTheme.warning : AppTheme.cyan,
                  title: contact.displayName,
                  subtitle:
                      '${contact.displayRelation} · ${contact.displayPhoneNumber}',
                  trailing: PopupMenuButton<String>(
                      iconColor: Colors.white70,
                      onSelected: (value) {
                        if (value == 'favorite') {
                          provider.toggleFavorite(contact);
                        }
                        if (value == 'edit') _edit(contact);
                        if (value == 'remove') {
                          provider.removeLocal(contact.contactId);
                        }
                      },
                      itemBuilder: (context) => const [
                            PopupMenuItem(
                                value: 'favorite',
                                child: Text('Toggle favorite')),
                            PopupMenuItem(value: 'edit', child: Text('Edit')),
                            PopupMenuItem(
                                value: 'remove', child: Text('Remove')),
                          ]),
                ),
              ),
            ),
            if (provider.error != null)
              Text(provider.error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ),
      ),
    );
  }
}
