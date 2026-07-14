import 'dart:io';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'result_screen.dart';

class ProcessingScreen extends StatefulWidget {
  final String imagePath;
  final ApiService apiService;

  const ProcessingScreen({
    Key? key,
    required this.imagePath,
    required this.apiService,
  }) : super(key: key);

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen> {
  String _selectedMode = 'auto';
  bool _isProcessing = false;
  String _processingStatus = '';
  double _progress = 0.0;

  final List<Map<String, dynamic>> _modes = [
    {
      'value': 'auto',
      'label': 'Auto',
      'icon': Icons.auto_awesome,
      'description': 'Balanced'
    },
    {
      'value': 'handwritten',
      'label': 'Handwritten',
      'icon': Icons.edit,
      'description': 'For notes'
    },
    {
      'value': 'printed',
      'label': 'Printed',
      'icon': Icons.text_fields,
      'description': 'Strong contrast'
    },
    {
      'value': 'color',
      'label': 'Color',
      'icon': Icons.palette,
      'description': 'Keep colors'
    },
  ];

  Future<void> _processDocument() async {
    setState(() {
      _isProcessing = true;
      _processingStatus = 'Uploading image...';
      _progress = 0.1;
    });

    try {
      // Simulate progress updates
      _updateProgress('Detecting edges...', 0.3);
      await Future.delayed(const Duration(milliseconds: 300));

      _updateProgress('Correcting perspective...', 0.5);
      await Future.delayed(const Duration(milliseconds: 300));

      _updateProgress('Enhancing image...', 0.7);
      await Future.delayed(const Duration(milliseconds: 300));

      _updateProgress('Extracting text...', 0.85);

      // Make API call
      final result = await widget.apiService.processDocument(
        widget.imagePath,
        _selectedMode,
      );

      _updateProgress('Complete!', 1.0);
      await Future.delayed(const Duration(milliseconds: 300));

      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => ResultScreen(
              processedImage: result['processed_image'],
              extractedText: result['extracted_text'] ?? '',
              originalPath: widget.imagePath,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isProcessing = false;
          _processingStatus = '';
          _progress = 0.0;
        });

        final errorMessage = e.toString().replaceAll('Exception: ', '');

        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Row(
              children: [
                Icon(Icons.error_outline, color: Colors.red),
                SizedBox(width: 8),
                Text('Processing Failed'),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(errorMessage),
                  const SizedBox(height: 16),
                  const Text(
                    'Quick fixes:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text('• Check backend is running'),
                  const Text('• Verify WiFi connection'),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
              ),
            ],
          ),
        );
      }
    }
  }

  void _updateProgress(String status, double progress) {
    if (mounted) {
      setState(() {
        _processingStatus = status;
        _progress = progress;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Process Document'),
        elevation: 0,
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Image Preview
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(
                      File(widget.imagePath),
                      width: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Enhancement Mode Selection
                  Text(
                    'Enhancement Mode',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 2.5,
                    ),
                    itemCount: _modes.length,
                    itemBuilder: (context, index) {
                      final mode = _modes[index];
                      final isSelected = _selectedMode == mode['value'];
                      return InkWell(
                        onTap: _isProcessing
                            ? null
                            : () {
                                setState(() {
                                  _selectedMode = mode['value'];
                                });
                              },
                        borderRadius: BorderRadius.circular(12),
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? Colors.indigo
                                : Colors.grey.shade100,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isSelected
                                  ? Colors.indigo
                                  : Colors.grey.shade300,
                              width: 2,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                mode['icon'],
                                color: isSelected
                                    ? Colors.white
                                    : Colors.grey.shade700,
                                size: 24,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      mode['label'],
                                      style: TextStyle(
                                        color: isSelected
                                            ? Colors.white
                                            : Colors.grey.shade800,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 14,
                                      ),
                                    ),
                                    Text(
                                      mode['description'],
                                      style: TextStyle(
                                        color: isSelected
                                            ? Colors.white70
                                            : Colors.grey.shade600,
                                        fontSize: 10,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),

                  if (_isProcessing) ...[
                    const SizedBox(height: 32),
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        children: [
                          LinearProgressIndicator(
                            value: _progress,
                            backgroundColor: Colors.grey.shade300,
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              Colors.indigo,
                            ),
                            minHeight: 8,
                          ),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                _processingStatus,
                                style: TextStyle(
                                  color: Colors.indigo.shade700,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                '${(_progress * 100).toInt()}%',
                                style: TextStyle(
                                  color: Colors.indigo.shade700,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Action Buttons
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: SafeArea(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Main Process Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isProcessing ? null : () => _processDocument(),
                      icon: Icon(_isProcessing
                          ? Icons.hourglass_empty
                          : Icons.auto_fix_high),
                      label: Text(_isProcessing
                          ? 'Processing...'
                          : 'Process with OCR'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.indigo,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        disabledBackgroundColor: Colors.grey.shade300,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}