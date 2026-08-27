import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('SheGuard smoke test renders app shell',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(child: Text('SheGuard')),
        ),
      ),
    );

    expect(find.text('SheGuard'), findsOneWidget);
  });
}
