class EmergencyContact {
  const EmergencyContact({
    this.contactId,
    required this.userId,
    required this.contactName,
    required this.relation,
    required this.phoneNumber,
    this.isFavorite = false,
    this.isHidden = false,
    this.localName,
    this.localRelation,
    this.localPhoneNumber,
  });

  final int? contactId;
  final int userId;
  final String contactName;
  final String relation;
  final String phoneNumber;
  final bool isFavorite;
  final bool isHidden;
  final String? localName;
  final String? localRelation;
  final String? localPhoneNumber;

  String get displayName =>
      localName?.trim().isNotEmpty == true ? localName! : contactName;
  String get displayRelation =>
      localRelation?.trim().isNotEmpty == true ? localRelation! : relation;
  String get displayPhoneNumber => localPhoneNumber?.trim().isNotEmpty == true
      ? localPhoneNumber!
      : phoneNumber;

  factory EmergencyContact.fromJson(Map<String, dynamic> json) {
    return EmergencyContact(
      contactId: (json['contact_id'] as num?)?.toInt(),
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      contactName: json['contact_name'] as String? ?? '',
      relation: json['relation'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
    );
  }

  EmergencyContact copyWith({
    bool? isFavorite,
    bool? isHidden,
    String? localName,
    String? localRelation,
    String? localPhoneNumber,
  }) {
    return EmergencyContact(
      contactId: contactId,
      userId: userId,
      contactName: contactName,
      relation: relation,
      phoneNumber: phoneNumber,
      isFavorite: isFavorite ?? this.isFavorite,
      isHidden: isHidden ?? this.isHidden,
      localName: localName ?? this.localName,
      localRelation: localRelation ?? this.localRelation,
      localPhoneNumber: localPhoneNumber ?? this.localPhoneNumber,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'contact_name': contactName,
      'relation': relation,
      'phone_number': phoneNumber,
    };
  }
}
