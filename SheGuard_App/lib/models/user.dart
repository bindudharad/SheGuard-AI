class User {
  const User({
    required this.userId,
    required this.fullName,
    required this.phoneNumber,
    this.profilePhoto,
  });

  final int userId;
  final String fullName;
  final String phoneNumber;
  final String? profilePhoto;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      userId: (json['user_id'] as num).toInt(),
      fullName: json['full_name'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      profilePhoto: json['profile_photo'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'full_name': fullName,
      'phone_number': phoneNumber,
      'profile_photo': profilePhoto,
    };
  }
}
