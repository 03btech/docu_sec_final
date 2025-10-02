from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api.client import APIClient
import os

class UploadWorker(QThread):
    """Worker thread for file upload to avoid blocking the UI."""
    finished = pyqtSignal(dict)  # Emits the upload result
    error = pyqtSignal(str)      # Emits error message

    def __init__(self, api_client, file_path):
        super().__init__()
        self.api_client = api_client
        self.file_path = file_path

    def run(self):
        try:
            result = self.api_client.upload_file(self.file_path)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Upload failed: Unknown error")
        except Exception as e:
            self.error.emit(f"Upload failed: {str(e)}")

class UploadDocumentView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.selected_file_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Upload Document")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Description
        description = QLabel("Select a document to upload. The system will automatically classify it and store it securely.")
        description.setStyleSheet("font-size: 14px; color: #6f7172; margin-bottom: 30px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        # File Selection Section
        file_section = QWidget()
        file_layout = QVBoxLayout(file_section)

        # File selection button and label
        select_file_layout = QHBoxLayout()

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #cccccc; border-radius: 5px; background-color: #f9f9f9;")
        self.file_label.setMinimumHeight(40)

        select_file_button = QPushButton("Select File")
        select_file_button.clicked.connect(self.select_file)

        select_file_layout.addWidget(self.file_label)
        select_file_layout.addWidget(select_file_button)

        file_layout.addLayout(select_file_layout)

        # File type hint
        file_hint = QLabel("Supported formats: PDF, DOCX, TXT, and other common document types")
        file_hint.setStyleSheet("font-size: 12px; color: #6f7172; margin-top: 5px;")
        file_layout.addWidget(file_hint)

        layout.addWidget(file_section)

        # Upload Section
        upload_section = QWidget()
        upload_layout = QVBoxLayout(upload_section)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        upload_layout.addWidget(self.progress_bar)

        # Upload button
        self.upload_button = QPushButton("Upload Document")
        self.upload_button.clicked.connect(self.upload_file)
        self.upload_button.setEnabled(False)  # Disabled until file is selected
        upload_layout.addWidget(self.upload_button)

        layout.addWidget(upload_section)

        # Add stretch to push everything to the top
        layout.addStretch()

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document to Upload",
            "",
            "All Files (*);;PDF Files (*.pdf);;Word Documents (*.docx);;Text Files (*.txt)"
        )

        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.setText(filename)
            self.upload_button.setEnabled(True)

    def upload_file(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File Selected", "Please select a file to upload first.")
            return

        # Disable upload button and show progress
        self.upload_button.setEnabled(False)
        self.progress_bar.setVisible(True)

        # Start upload in background thread
        self.upload_worker = UploadWorker(self.api_client, self.selected_file_path)
        self.upload_worker.finished.connect(self.on_upload_finished)
        self.upload_worker.error.connect(self.on_upload_error)
        self.upload_worker.start()

    def on_upload_finished(self, result):
        # Hide progress and re-enable button
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)

        # Show success message
        filename = result.get('filename', 'Document')
        classification = result.get('classification', 'unclassified')
        QMessageBox.information(
            self,
            "Upload Successful",
            f"Document '{filename}' has been uploaded successfully!\n\n"
            f"Classification: {classification}\n\n"
            f"The document is now available in your 'My Documents' section."
        )

        # Clear selection
        self.selected_file_path = None
        self.file_label.setText("No file selected")
        self.upload_button.setEnabled(False)

    def on_upload_error(self, error_message):
        # Hide progress and re-enable button
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)

        # Show error message
        QMessageBox.critical(self, "Upload Failed", error_message)