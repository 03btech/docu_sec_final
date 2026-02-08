from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFileDialog, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from api.client import APIClient
import os

# Stage definitions: (status_key, progress_percent, display_label)
CLASSIFICATION_STAGES = [
    ("queued",           10,  "Queued..."),
    ("extracting_text",  40,  "Extracting text..."),
    ("classifying",      75,  "Classifying with AI..."),
    ("completed",        100, "Classification complete"),
    ("failed",           100, "Classification failed"),
]
STAGE_MAP = {s[0]: (s[1], s[2]) for s in CLASSIFICATION_STAGES}


class UploadWorker(QThread):
    """Worker thread for file upload (save + create record only, returns immediately)."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

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


class PollWorker(QThread):
    """Worker thread for polling classification status.

    Runs the blocking HTTP request off the main thread to prevent
    UI freezes during network latency, rate-limit delays, or timeouts.
    Emits result signal with status data (or None on failure)."""
    result = pyqtSignal(object)  # dict or None

    def __init__(self, api_client, doc_id):
        super().__init__()
        self.api_client = api_client
        self.doc_id = doc_id

    def run(self):
        status_data = self.api_client.get_classification_status(self.doc_id)
        self.result.emit(status_data)


class UploadDocumentView(QWidget):
    # Maximum polling duration: 5 minutes at 1s intervals
    MAX_POLL_COUNT = 300

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.selected_file_path = None
        self.poll_timer = None
        self.current_doc_id = None
        self.poll_count = 0
        self._poll_in_flight = False   # overlap guard for PollWorker
        self._poll_worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Upload Document")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Description
        description = QLabel("Select a document to upload. The system will automatically "
                             "classify it and store it securely.")
        description.setStyleSheet("font-size: 14px; color: #6f7172; margin-bottom: 30px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        # File Selection Section
        file_section = QWidget()
        file_layout = QVBoxLayout(file_section)

        select_file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(
            "font-size: 14px; padding: 8px; border: 1px solid #cccccc; "
            "border-radius: 5px; background-color: #f9f9f9;"
        )
        self.file_label.setMinimumHeight(40)

        select_file_button = QPushButton("Select File")
        select_file_button.clicked.connect(self.select_file)

        select_file_layout.addWidget(self.file_label)
        select_file_layout.addWidget(select_file_button)
        file_layout.addLayout(select_file_layout)

        file_hint = QLabel("Supported formats: PDF, DOCX, TXT")
        file_hint.setStyleSheet("font-size: 12px; color: #6f7172; margin-top: 5px;")
        file_layout.addWidget(file_hint)
        layout.addWidget(file_section)

        # Upload Section
        upload_section = QWidget()
        upload_layout = QVBoxLayout(upload_section)

        # Determinate progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)          # Determinate: 0-100%
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        upload_layout.addWidget(self.progress_bar)

        # Stage label (hidden initially)
        self.stage_label = QLabel("")
        self.stage_label.setStyleSheet("font-size: 12px; color: #4a90d9; margin-top: 4px;")
        self.stage_label.setVisible(False)
        upload_layout.addWidget(self.stage_label)

        # Upload button
        self.upload_button = QPushButton("Upload Document")
        self.upload_button.clicked.connect(self.upload_file)
        self.upload_button.setEnabled(False)
        upload_layout.addWidget(self.upload_button)

        layout.addWidget(upload_section)
        layout.addStretch()

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document to Upload", "",
            "Supported Documents (*.pdf *.docx *.txt);;PDF Files (*.pdf);;Word Documents (*.docx);;Text Files (*.txt)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.upload_button.setEnabled(True)

    def upload_file(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File Selected", "Please select a file first.")
            return

        # P0-REVIEW-4: Stop any existing poll timer and worker BEFORE starting
        # a new upload. Prevents stale PollWorker from corrupting progress display.
        if self.poll_timer and self.poll_timer.isActive():
            self.poll_timer.stop()
        if self._poll_worker is not None:
            if self._poll_worker.isRunning():
                self._poll_worker.quit()
                self._poll_worker.wait(500)
            self._poll_worker.deleteLater()
            self._poll_worker = None
        self._poll_in_flight = False
        self.current_doc_id = None

        # Show progress UI
        self.upload_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(5)
        self.stage_label.setVisible(True)
        self.stage_label.setText("Uploading file...")

        # Start upload in background thread
        self.upload_worker = UploadWorker(self.api_client, self.selected_file_path)
        self.upload_worker.finished.connect(self.on_upload_finished)
        self.upload_worker.error.connect(self.on_upload_error)
        self.upload_worker.start()

    def on_upload_finished(self, result):
        """File saved on server — now poll for classification progress."""
        self.current_doc_id = result.get("id")
        self.progress_bar.setValue(10)
        self.stage_label.setText("Queued for classification...")

        # Start polling every 1 second (with timeout safety)
        self.poll_count = 0
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_classification_status)
        self.poll_timer.start(1000)

    def poll_classification_status(self):
        """Kick off a PollWorker thread to check status without blocking the UI."""
        self.poll_count += 1
        if self.poll_count > self.MAX_POLL_COUNT:
            self.poll_timer.stop()
            self.on_upload_error(
                "Classification timed out after 5 minutes. "
                "The document was saved but classification may still be in progress. "
                "Check the document status in 'My Documents'."
            )
            return

        # Prevent overlapping poll requests
        if self._poll_in_flight:
            return
        self._poll_in_flight = True

        # Clean up previous PollWorker to prevent QThread accumulation
        if self._poll_worker is not None:
            self._poll_worker.deleteLater()

        self._poll_worker = PollWorker(self.api_client, self.current_doc_id)
        self._poll_worker.result.connect(self._handle_poll_result)
        self._poll_worker.start()

    def _handle_poll_result(self, status_data):
        """Handle the result from PollWorker (runs on main thread via signal)."""
        self._poll_in_flight = False   # allow next poll tick
        if not status_data:
            return  # Network hiccup, try again next tick

        status = status_data.get("status", "queued")

        # Handle rate limiting — back off the poll interval temporarily
        if status == "rate_limited":
            self.poll_timer.setInterval(3000)  # Slow down to 3s
            return

        # Restore normal interval if we were backed off
        if self.poll_timer.interval() != 1000:
            self.poll_timer.setInterval(1000)

        progress, label = STAGE_MAP.get(status, (10, "Processing..."))

        self.progress_bar.setValue(progress)
        self.stage_label.setText(label)

        if status == "completed":
            self.poll_timer.stop()
            self._show_success({
                "filename": os.path.basename(self.selected_file_path) if self.selected_file_path else "Document",
                "classification": status_data.get("classification", "unclassified"),
            })
        elif status == "failed":
            self.poll_timer.stop()
            error_msg = status_data.get("error", "Classification failed")
            self.on_upload_error(f"Classification failed: {error_msg}")

    def _show_success(self, result):
        """Show success dialog and reset UI."""
        self.progress_bar.setVisible(False)
        self.stage_label.setVisible(False)
        self.upload_button.setEnabled(True)

        filename = result.get("filename", "Document")
        classification = result.get("classification", "unclassified")
        QMessageBox.information(
            self, "Upload Successful",
            f"Document '{filename}' has been uploaded successfully!\n\n"
            f"Classification: {classification}\n\n"
            f"The document is now available in your 'My Documents' section."
        )

        self.selected_file_path = None
        self.current_doc_id = None
        self.file_label.setText("No file selected")
        self.upload_button.setEnabled(False)

    def on_upload_error(self, error_message):
        """Show error and reset UI. Offers retry if classification failed but doc was saved."""
        if self.poll_timer:
            self.poll_timer.stop()
        self.progress_bar.setVisible(False)
        self.stage_label.setVisible(False)
        self.upload_button.setEnabled(True)

        # Offer retry for classification failures (document is already saved)
        if self.current_doc_id:
            retry = QMessageBox.question(
                self, "Retry Classification?",
                "The document was saved but classification failed.\n"
                "Would you like to retry classification?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if retry == QMessageBox.StandardButton.Yes:
                try:
                    self.api_client.retry_classification(self.current_doc_id)
                    # Restart polling
                    self.poll_count = 0
                    self._poll_in_flight = False
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setValue(10)
                    self.stage_label.setVisible(True)
                    self.stage_label.setText("Retrying classification...")
                    self.upload_button.setEnabled(False)
                    self.poll_timer = QTimer()
                    self.poll_timer.timeout.connect(self.poll_classification_status)
                    self.poll_timer.start(1000)
                    return
                except Exception:
                    QMessageBox.critical(self, "Retry Failed", "Could not retry classification.")

        # Clear doc ID after retry check (not before)
        self.current_doc_id = None
        QMessageBox.critical(self, "Upload Failed", error_message)

    def closeEvent(self, event):
        """P3-16 / P2-14: Clean up QTimer and PollWorker on widget close."""
        if self.poll_timer and self.poll_timer.isActive():
            self.poll_timer.stop()
        if self._poll_worker is not None:
            if self._poll_worker.isRunning():
                self._poll_worker.quit()
                self._poll_worker.wait(1000)
            self._poll_worker.deleteLater()
            self._poll_worker = None
        super().closeEvent(event)