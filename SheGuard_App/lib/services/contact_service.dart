import '../models/emergency_contact.dart';
import 'api_service.dart';

class ContactService {
  ContactService(this._api);

  final ApiService _api;

  Future<List<EmergencyContact>> fetchContacts(int userId) async {
    final json = await _api.getJson('/contacts/$userId');
    final rows = (json['contacts'] as List? ?? const []);
    return rows
        .map((item) => EmergencyContact.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<EmergencyContact> addContact(EmergencyContact contact) async {
    final json = await _api.postJson('/contacts/add', contact.toJson());
    return EmergencyContact.fromJson(json);
  }
}
