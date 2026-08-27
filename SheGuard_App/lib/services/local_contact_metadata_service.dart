import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class ContactMetadata {
  const ContactMetadata({
    this.isFavorite = false,
    this.isHidden = false,
    this.name,
    this.relation,
    this.phoneNumber,
  });

  final bool isFavorite;
  final bool isHidden;
  final String? name;
  final String? relation;
  final String? phoneNumber;

  factory ContactMetadata.fromJson(Map<String, dynamic> json) {
    return ContactMetadata(
      isFavorite: json['is_favorite'] as bool? ?? false,
      isHidden: json['is_hidden'] as bool? ?? false,
      name: json['name'] as String?,
      relation: json['relation'] as String?,
      phoneNumber: json['phone_number'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'is_favorite': isFavorite,
      'is_hidden': isHidden,
      'name': name,
      'relation': relation,
      'phone_number': phoneNumber,
    };
  }

  ContactMetadata copyWith({
    bool? isFavorite,
    bool? isHidden,
    String? name,
    String? relation,
    String? phoneNumber,
  }) {
    return ContactMetadata(
      isFavorite: isFavorite ?? this.isFavorite,
      isHidden: isHidden ?? this.isHidden,
      name: name ?? this.name,
      relation: relation ?? this.relation,
      phoneNumber: phoneNumber ?? this.phoneNumber,
    );
  }
}

class LocalContactMetadataService {
  static const _key = 'contact_metadata';

  Future<Map<int, ContactMetadata>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return {};
    final decoded = jsonDecode(raw) as Map<String, dynamic>;
    return decoded.map(
      (key, value) => MapEntry(
        int.parse(key),
        ContactMetadata.fromJson(value as Map<String, dynamic>),
      ),
    );
  }

  Future<void> save(Map<int, ContactMetadata> metadata) async {
    final prefs = await SharedPreferences.getInstance();
    final encoded = metadata.map(
      (key, value) => MapEntry(key.toString(), value.toJson()),
    );
    await prefs.setString(_key, jsonEncode(encoded));
  }
}
