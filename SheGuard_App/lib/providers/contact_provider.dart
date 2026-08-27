import 'package:flutter/foundation.dart';

import '../models/emergency_contact.dart';
import '../services/contact_service.dart';
import '../services/local_contact_metadata_service.dart';

class ContactProvider extends ChangeNotifier {
  ContactProvider(this._contactService, this._metadataService);

  final ContactService _contactService;
  final LocalContactMetadataService _metadataService;

  List<EmergencyContact> contacts = [];
  Map<int, ContactMetadata> _metadata = {};
  bool loading = false;
  String? error;

  List<EmergencyContact> get visibleContacts =>
      contacts.where((contact) => !contact.isHidden).toList()
        ..sort((a, b) {
          if (a.isFavorite == b.isFavorite) return 0;
          return a.isFavorite ? -1 : 1;
        });

  Future<void> load(int userId) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      _metadata = await _metadataService.load();
      final fetched = await _contactService.fetchContacts(userId);
      contacts = fetched.map(_applyMetadata).toList();
      debugPrint('SheGuard contacts synced: ${contacts.length}');
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> add(EmergencyContact contact) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final saved = await _contactService.addContact(contact);
      contacts = [_applyMetadata(saved), ...contacts];
      debugPrint('SheGuard contact added and synced: ${saved.contactId}');
      return true;
    } catch (e) {
      error = e.toString();
      return false;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> removeLocal(int? contactId) async {
    if (contactId == null) return;
    final current = _metadata[contactId] ?? const ContactMetadata();
    _metadata[contactId] = current.copyWith(isHidden: true);
    await _metadataService.save(_metadata);
    contacts = contacts
        .map((item) =>
            item.contactId == contactId ? item.copyWith(isHidden: true) : item)
        .toList();
    debugPrint('SheGuard contact hidden locally: $contactId');
    notifyListeners();
  }

  Future<void> toggleFavorite(EmergencyContact contact) async {
    final id = contact.contactId;
    if (id == null) return;
    final current = _metadata[id] ?? const ContactMetadata();
    _metadata[id] = current.copyWith(isFavorite: !contact.isFavorite);
    await _metadataService.save(_metadata);
    contacts = contacts
        .map((item) => item.contactId == id
            ? item.copyWith(isFavorite: !contact.isFavorite)
            : item)
        .toList();
    debugPrint('SheGuard contact favorite toggled locally: $id');
    notifyListeners();
  }

  Future<void> editLocal(
    EmergencyContact contact, {
    required String name,
    required String relation,
    required String phoneNumber,
  }) async {
    final id = contact.contactId;
    if (id == null) return;
    final current = _metadata[id] ?? const ContactMetadata();
    _metadata[id] = current.copyWith(
      name: name,
      relation: relation,
      phoneNumber: phoneNumber,
    );
    await _metadataService.save(_metadata);
    contacts = contacts
        .map((item) => item.contactId == id
            ? item.copyWith(
                localName: name,
                localRelation: relation,
                localPhoneNumber: phoneNumber,
              )
            : item)
        .toList();
    debugPrint('SheGuard contact edited locally: $id');
    notifyListeners();
  }

  EmergencyContact _applyMetadata(EmergencyContact contact) {
    final id = contact.contactId;
    if (id == null) return contact;
    final metadata = _metadata[id];
    if (metadata == null) return contact;
    return contact.copyWith(
      isFavorite: metadata.isFavorite,
      isHidden: metadata.isHidden,
      localName: metadata.name,
      localRelation: metadata.relation,
      localPhoneNumber: metadata.phoneNumber,
    );
  }
}
