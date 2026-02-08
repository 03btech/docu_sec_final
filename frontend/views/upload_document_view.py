from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFileDialog, QMessageBox, QProgressBar,
                              QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import qtawesome as qta
from api.client import APIClient
import os

# Stage definitions: (status_key, progress_percent, display_label, icon)
CLASSIFICATION_STAGES = [
    ("queued",           10,  "Queued for processing",       "fa5s.clock"),
    ("extracting_text",  40,  "Extracting text content...",  "fa5s.file-alt"),
    ("classifying",      75,  "Classifying with AI...",      "fa5s.brain"),
    ("completed",        100, "Classification complete",     "fa5s.check-circle"),
    ("failed",           100, "Classification failed",       "fa5s.times-circle"),
]
STAGE_MAP = {s[0]: (s[1], s[2], s[3]) for s in CLASSIFICATION_STAGES}


class UploadWorker(QThread):
    """Worker thread for file upload."""
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
    """Worker thread for polling classification status."""
    result = pyqtSignal(object)

    def __init__(self, api_client, doc_id):
        super().__init__()
        self.api_client = api_client
        self.doc_id = doc_id

    def run(self):
        status_data = self.api_client.get_classification_status(self.doc_id)
        self.result.emit(status_data)


class DropZone(QFrame):
    """Drag-and-drop zone for file selection."""
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._hovered = False
        self._apply_style()

    def _apply_style(self):
        border_color = "#27ae60" if self._hovered else "#d1d5db"
        bg = "#f0fdf4" if self._hovered else "#f9fafb"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px dashed {border_color};
                border-radius: 12px;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self._hovered = True
            self._apply_style()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hovered = False
        self._apply_style()

    def dropEvent(self, event: QDropEvent):
        self._hovered = False
        self._apply_style()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.pdf', '.docx', '.txt'):
                self.file_dropped.emit(path)
            else:
                QMessageBox.warning(self, "Unsupported File",
                                    f"'{ext}' is not supported.\nUse PDF, DOCX, or TXT.")


class UploadDocumentView(QWidget):
    MAX_POLL_COUNT = 300

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.selected_file_path = None
        self.poll_timer = None
        self.current_doc_id = None
        self.poll_count = 0
        self._poll_in_flight = False
        self._poll_worker = None
        self.setup_ui()

    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Upload Document")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)

        description = QLabel("Upload a document and the system will automatically classify "
                             "it using AI and store it securely.")
        description.setStyleSheet("font-size: 14px; color: #6b7280; margin-bottom: 4px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        # ── Drop Zone Card ──
        drop_card = QFrame()
        drop_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
        """)
        drop_card_layout = QVBoxLayout(drop_card)
        drop_card_layout.setContentsMargins(20, 20, 20, 20)
        drop_card_layout.setSpacing(16)

        card_title = QLabel("Select File")
        card_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #1f2937; border: none;")
        drop_card_layout.addWidget(card_title)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.setFixedHeight(180)
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        dz_layout = QVBoxLayout(self.drop_zone)
        dz_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.cloud-upload-alt', color='#9ca3af').pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: none;")
        dz_layout.addWidget(icon_label)

        dz_text = QLabel("Drag & drop your file here")
        dz_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_text.setStyleSheet("font-size: 15px; font-weight: 500; color: #374151; border: none;")
        dz_layout.addWidget(dz_text)

        dz_sub = QLabel("or click the button below to browse")
        dz_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_sub.setStyleSheet("font-size: 13px; color: #9ca3af; border: none;")
        dz_layout.addWidget(dz_sub)

        drop_card_layout.addWidget(self.drop_zone)

        # Browse button row
        browse_row = QHBoxLayout()
        browse_row.setSpacing(12)

        self.browse_btn = QPushButton("  Browse Files")
        self.browse_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 8px; padding: 10px 20px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        self.browse_btn.clicked.connect(self.select_file)
        browse_row.addWidget(self.browse_btn)

        format_label = QLabel("Supported: PDF, DOCX, TXT")
        format_label.setStyleSheet("font-size: 12px; color: #9ca3af; border: none;")
        browse_row.addWidget(format_label)
        browse_row.addStretch()

        drop_card_layout.addLayout(browse_row)

        # Selected file info (hidden initially)
        self.file_info_frame = QFrame()
        self.file_info_frame.setStyleSheet("""
            QFrame {
                background-color: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 8px;
            }
        """)
        self.file_info_frame.setVisible(False)
        fi_layout = QHBoxLayout(self.file_info_frame)
        fi_layout.setContentsMargins(12, 10, 12, 10)

        fi_icon = QLabel()
        fi_icon.setPixmap(qta.icon('fa5s.file-alt', color='#27ae60').pixmap(20, 20))
        fi_icon.setStyleSheet("border: none;")
        fi_layout.addWidget(fi_icon)

        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #166534; border: none;")
        fi_layout.addWidget(self.file_name_label)

        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet("font-size: 12px; color: #6b7280; border: none;")
        fi_layout.addWidget(self.file_size_label)
        fi_layout.addStretch()

        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #6b7280; font-size: 14px; border-radius: 12px; }
            QPushButton:hover { background-color: #dcfce7; color: #166534; }
        """)
        clear_btn.clicked.connect(self._clear_file)
        fi_layout.addWidget(clear_btn)

        drop_card_layout.addWidget(self.file_info_frame)
        layout.addWidget(drop_card)

        # ── Progress Card (hidden initially) ──
        self.progress_card = QFrame()
        self.progress_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
        """)
        self.progress_card.setVisible(False)
        pc_layout = QVBoxLayout(self.progress_card)
        pc_layout.setContentsMargins(20, 20, 20, 20)
        pc_layout.setSpacing(12)

        pc_title = QLabel("Processing Document")
        pc_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #1f2937; border: none;")
        pc_layout.addWidget(pc_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e5e7eb;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 4px;
            }
        """)
        pc_layout.addWidget(self.progress_bar)

        stage_row = QHBoxLayout()
        self.stage_icon = QLabel()
        self.stage_icon.setStyleSheet("border: none;")
        self.stage_icon.setFixedSize(20, 20)
        stage_row.addWidget(self.stage_icon)
        self.stage_label = QLabel("")
        self.stage_label.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        stage_row.addWidget(self.stage_label)
        stage_row.addStretch()
        self.progress_pct = QLabel("0%")
        self.progress_pct.setStyleSheet("font-size: 13px; font-weight: 600; color: #27ae60; border: none;")
        stage_row.addWidget(self.progress_pct)
        pc_layout.addLayout(stage_row)

        layout.addWidget(self.progress_card)

        # ── Upload Button ──
        self.upload_button = QPushButton("  Upload & Classify")
        self.upload_button.setIcon(qta.icon('fa5s.cloud-upload-alt', color='white'))
        self.upload_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_button.setEnabled(False)
        self.upload_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 10px; padding: 14px 28px; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
            QPushButton:pressed { background-color: #1e8449; }
            QPushButton:disabled { background-color: #d1d5db; color: #9ca3af; }
        """)
        self.upload_button.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_button)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── File Selection ──

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Document to Upload", "",
            "Supported Documents (*.pdf *.docx *.txt);;PDF Files (*.pdf);;Word Documents (*.docx);;Text Files (*.txt)"
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, path: str):
        self.selected_file_path = path
        name = os.path.basename(path)
        size = os.path.getsize(path)
        self.file_name_label.setText(name)
        self.file_size_label.setText(self._format_size(size))
        self.file_info_frame.setVisible(True)
        self.upload_button.setEnabled(True)

    def _clear_file(self):
        self.selected_file_path = None
        self.file_info_frame.setVisible(False)
        self.upload_button.setEnabled(False)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    # ── Upload ──

    def upload_file(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File Selected", "Please select a file first.")
            return

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

        self.upload_button.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_card.setVisible(True)
        self._set_stage("fa5s.cloud-upload-alt", "Uploading file...", 5)

        self.upload_worker = UploadWorker(self.api_client, self.selected_file_path)
        self.upload_worker.finished.connect(self.on_upload_finished)
        self.upload_worker.error.connect(self.on_upload_error)
        self.upload_worker.start()

    def _set_stage(self, icon_name: str, text: str, pct: int):
        self.stage_icon.setPixmap(qta.icon(icon_name, color='#27ae60').pixmap(18, 18))
        self.stage_label.setText(text)
        self.progress_bar.setValue(pct)
        self.progress_pct.setText(f"{pct}%")

    def on_upload_finished(self, result):
        self.current_doc_id = result.get("id")
        self._set_stage("fa5s.clock", "Queued for classification...", 10)

        self.poll_count = 0
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_classification_status)
        self.poll_timer.start(1000)

    def poll_classification_status(self):
        self.poll_count += 1
        if self.poll_count > self.MAX_POLL_COUNT:
            self.poll_timer.stop()
            self.on_upload_error(
                "Classification timed out after 5 minutes. "
                "The document was saved but classification may still be in progress. "
                "Check the document status in 'My Documents'."
            )
            return

        if self._poll_in_flight:
            return
        self._poll_in_flight = True

        if self._poll_worker is not None:
            self._poll_worker.deleteLater()

        self._poll_worker = PollWorker(self.api_client, self.current_doc_id)
        self._poll_worker.result.connect(self._handle_poll_result)
        self._poll_worker.start()

    def _handle_poll_result(self, status_data):
        self._poll_in_flight = False
        if not status_data:
            return

        status = status_data.get("status", "queued")

        if status == "rate_limited":
            self.poll_timer.setInterval(3000)
            return

        if self.poll_timer.interval() != 1000:
            self.poll_timer.setInterval(1000)

        progress, label, icon = STAGE_MAP.get(status, (10, "Processing...", "fa5s.spinner"))
        self._set_stage(icon, label, progress)

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
        self.progress_card.setVisible(False)
        self.upload_button.setEnabled(True)
        self.browse_btn.setEnabled(True)

        filename = result.get("filename", "Document")
        classification = result.get("classification", "unclassified")

        # Show inline success
        self._set_stage("fa5s.check-circle", "Classification complete", 100)
        self.progress_card.setVisible(True)
        self.stage_label.setStyleSheet("font-size: 13px; color: #166534; font-weight: 600; border: none;")
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #e5e7eb; border: none; border-radius: 4px; }
            QProgressBar::chunk { background-color: #22c55e; border-radius: 4px; }
        """)

        QMessageBox.information(
            self, "Upload Successful",
            f"Document '{filename}' has been uploaded successfully!\n\n"
            f"Classification: {classification}\n\n"
            f"The document is now available in your 'My Documents' section."
        )

        # Reset
        self._clear_file()
        self.current_doc_id = None
        self.progress_card.setVisible(False)
        self.stage_label.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #e5e7eb; border: none; border-radius: 4px; }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 4px; }
        """)

    def on_upload_error(self, error_message):
        if self.poll_timer:
            self.poll_timer.stop()
        self.progress_card.setVisible(False)
        self.upload_button.setEnabled(True)
        self.browse_btn.setEnabled(True)

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
                    self.poll_count = 0
                    self._poll_in_flight = False
                    self.progress_card.setVisible(True)
                    self._set_stage("fa5s.redo", "Retrying classification...", 10)
                    self.upload_button.setEnabled(False)
                    self.browse_btn.setEnabled(False)
                    self.poll_timer = QTimer()
                    self.poll_timer.timeout.connect(self.poll_classification_status)
                    self.poll_timer.start(1000)
                    return
                except Exception:
                    QMessageBox.critical(self, "Retry Failed", "Could not retry classification.")

        self.current_doc_id = None
        QMessageBox.critical(self, "Upload Failed", error_message)

    def refresh_data(self):
        """No-op — nothing to refresh, but keeps interface consistent."""
        pass

    def closeEvent(self, event):
        if self.poll_timer and self.poll_timer.isActive():
            self.poll_timer.stop()
        if self._poll_worker is not None:
            if self._poll_worker.isRunning():
                self._poll_worker.quit()
                self._poll_worker.wait(1000)
            self._poll_worker.deleteLater()
            self._poll_worker = None
        super().closeEvent(event)
