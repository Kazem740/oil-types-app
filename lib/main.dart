import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize database
  final dbPath = await getDatabasesPath();
  final path = join(dbPath, 'alka_oil.db');
  
  // Copy database if it exists in documents
  final appDir = await getApplicationDocumentsDirectory();
  final sourceDbPath = join(appDir.path, 'ALKA_Data', 'alka_oil.db');
  if (await File(sourceDbPath).exists()) {
    await File(sourceDbPath).copy(path);
  }
  
  final db = await openDatabase(
    path,
    version: 1,
    onCreate: (Database db, int version) async {
      await db.execute('''
        CREATE TABLE IF NOT EXISTS oil_types (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          remaining_distance INTEGER NOT NULL
        )
      ''');
    },
  );
  
  runApp(
    MultiProvider(
      providers: [
        Provider<Database>.value(value: db),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ALKA Oil Tracker',
      locale: const Locale('ar'),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('ar'),
      ],
      theme: ThemeData(
        primarySwatch: Colors.blue,
        textTheme: GoogleFonts.cairoTextTheme(),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ALKA Oil Tracker'),
      ),
      body: FutureBuilder<List<Map>>(
        future: Provider.of<Database>(context).query('oil_types'),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          
          final oilTypes = snapshot.data!;
          if (oilTypes.isEmpty) {
            return const Center(
              child: Text(
                'لا يوجد أنواع زيوت مضافة',
                style: TextStyle(fontSize: 18),
              ),
            );
          }
          
          return ListView.builder(
            itemCount: oilTypes.length,
            itemBuilder: (context, index) {
              final oil = oilTypes[index];
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: ListTile(
                  title: Text(oil['name']),
                  subtitle: Text('المسافة المتبقية: ${oil['remaining_distance']} كم'),
                  trailing: const Icon(Icons.arrow_forward_ios),
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Add new oil type
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
