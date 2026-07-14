import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  // IMPORTANT: Change this to your computer's IP address
  // To find your IP:
  // Windows: Open CMD and type 'ipconfig', look for IPv4 Address
  // Mac: Open Terminal and type 'ifconfig | grep "inet "'
  //
  // Example: static const String baseUrl = 'http://192.168.1.100:8000';
  //
  // Make sure your phone and computer are on the SAME WiFi network!
 static const String baseUrl = 'http://10.0.2.2:8000'; // For emulator
// static const String baseUrl = 'http://192.168.1.11:8000'; // For physical phone

  // For testing without backend, set this to true
  static const bool useMockData = false;

  /// Processes a document image using the backend API
  Future<Map<String, dynamic>> processDocument(
    String imagePath,
    String mode,
  ) async {
    // Mock data for testing without backend
    if (useMockData) {
      await Future.delayed(const Duration(seconds: 2));

      final bytes = await File(imagePath).readAsBytes();
      final base64Image = base64Encode(bytes);

      return {
        'success': true,
        'processed_image': 'data:image/jpeg;base64,$base64Image',
        'extracted_text': '''
This is a sample extracted text. In a real scenario, this would be the text extracted from your document using OCR (Optical Character Recognition). The Smart Scan app uses:
- Edge detection to find document boundaries
- Perspective correction to flatten the image
- Image enhancement (grayscale, B&W, or color)
- Tesseract OCR for text extraction

To use the real backend:
1. Set useMockData = false in api_service.dart
2. Update baseUrl to your computer's IP address
3. Make sure the Python backend is running
4. Ensure your phone and computer are on the same WiFi
''',
        'mode': mode,
        'contour_found': true,
      };
    }

    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/process'),
      );

      // Add the image file
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          imagePath,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      // Add the mode parameter
      request.fields['mode'] = mode;

      // Send request with timeout
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),  // Changed from 30 to 60
        onTimeout: () {
          throw Exception('Connection timeout. Please check:\n'
              '1. Backend is running on your computer\n'
              '2. Computer IP address is correct in api_service.dart\n'
              '3. Phone and computer are on same WiFi\n'
              '4. Windows Firewall allows port 8000');
        },
      );

      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Server error: ${response.statusCode}\n${response.body}');
      }
    } on SocketException {
      throw Exception('Cannot connect to backend.\n\n'
          'Please check:\n'
          '1. Backend is running: python main.py\n'
          '2. Update baseUrl in api_service.dart to your computer\'s IP\n'
          '3. Phone and computer on same WiFi\n'
          '4. Firewall allows connections\n\n'
          'Current URL: $baseUrl');
    } on http.ClientException {
      throw Exception('Connection failed.\n\n'
          'Make sure:\n'
          '1. Python backend is running\n'
          '2. IP address is correct: $baseUrl\n'
          '3. Both devices on same network');
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  /// Detects edges in an image using the backend API
  Future<Map<String, dynamic>> detectEdges(String imagePath) async {
    // Mock data for testing without backend
    if (useMockData) {
      await Future.delayed(const Duration(seconds: 1));

      final bytes = await File(imagePath).readAsBytes();
      final base64Image = base64Encode(bytes);

      return {
        'success': true,
        'preview_image': 'data:image/jpeg;base64,$base64Image',
        'contour_found': true,
      };
    }

    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/detect-edges'),
      );

      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          imagePath,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
      );

      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to detect edges: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error detecting edges: $e');
    }
  }

  /// Test connection to backend
  Future<bool> testConnection() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/')).timeout(
        const Duration(seconds: 5),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
