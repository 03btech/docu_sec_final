"""
Base Document View - Shared functionality for all document list views.
Eliminates duplication across My Documents, Department, Public, and Shared views.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QMessageBox, QFileDialog, 
                              QPushButton, QHBoxLayout, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api.client import APIClient
from widgets.document_card_table import ModernDocumentTable
from .document_viewer import DocumentViewer
from .secure_document_viewer import SecureDocumentViewer
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.camera_utils import check_camera_available


class DocumentLoadWorker(QThread):
    """Worker thread that loads documents off the main thread."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, load_fn):
        super().__init__()
        self._load_fn = load_fn

    def run(self):
        try:
            docs = self._load_fn()
            self.finished.emit(docs if docs else [])
        except Exception as e:
            self.error.emit(str(e))


class BaseDocumentView(QWidget):
    """
    Base class for document list views (My Documents, Department, Public, Shared).

    Subclasses must set:
        view_title: str           — e.g. "My Documents"
        view_description: str     — e.g. "Documents you own and have uploaded"

    Subclasses must implement:
        fetch_documents() -> list — return documents from the API
        get_action_callbacks(row) -> dict — return allowed actions per row
    """

    view_title: str = "Documents"
    view_description: str = ""

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.documents = []
        self._load_worker = None
        self.setup_ui()
        self.load_documents()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title = QLabel(self.view_title)
        title.setStyleSheet("QLabel { font-size: 28px; font-weight: bold; color: #1f2937; }")
        header_layout.addWidget(title)

        if self.view_description:
            desc = QLabel(self.view_description)
            desc.setStyleSheet("QLabel { font-size: 14px; color: #6b7280; }")
            header_layout.addWidget(desc)

        layout.addWidget(header)

        # Action bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)

        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
        """)
        refresh_button.clicked.connect(self.load_documents)
        action_bar.addWidget(refresh_button)

        # Search input
        from PyQt6.QtWidgets import QLineEdit
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                max-width: 300px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
            }
        """)
        self.search_input.textChanged.connect(self._apply_search_filter)
        action_bar.addWidget(self.search_input)

        action_bar.addStretch()
        layout.addLayout(action_bar)

        # Loading label (hidden by default)
        self.loading_label = QLabel("Loading documents...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 14px;
                padding: 40px;
            }
        """)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Empty state label (hidden by default)
        self.empty_label = QLabel("")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 16px;
                padding: 60px 20px;
            }
        """)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Document table
        self.table = ModernDocumentTable()
        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # Data Loading (off main thread)
    # ------------------------------------------------------------------

    def load_documents(self):
        """Load documents using a background worker thread."""
        self.loading_label.setVisible(True)
        self.empty_label.setVisible(False)
        self.table.setVisible(False)

        self._load_worker = DocumentLoadWorker(self.fetch_documents)
        self._load_worker.finished.connect(self._on_documents_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_documents_loaded(self, documents):
        self.loading_label.setVisible(False)
        self.documents = documents

        if not documents:
            self.empty_label.setText(self._empty_state_message())
            self.empty_label.setVisible(True)
            self.table.setVisible(False)
        else:
            self.empty_label.setVisible(False)
            self.table.setVisible(True)
            self._populate_table()

    def _on_load_error(self, error_msg):
        self.loading_label.setVisible(False)
        self.table.setVisible(True)
        QMessageBox.critical(self, "Error", f"Failed to load documents: {error_msg}")

    def _populate_table(self):
        """Populate the table, applying any active search filter."""
        search = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ""
        if search:
            filtered = [d for d in self.documents 
                        if search in d.get('filename', '').lower()
                        or search in d.get('classification', '').lower()]
        else:
            filtered = self.documents

        if not filtered and self.documents:
            self.empty_label.setText("No documents match your search.")
            self.empty_label.setVisible(True)
            self.table.setVisible(False)
        else:
            self.empty_label.setVisible(False)
            self.table.setVisible(True)
            # We need a wrapper that maps row back to the filtered list
            self._filtered_docs = filtered
            self.table.set_documents_with_row_callbacks(filtered, self._get_filtered_callbacks)

    def _get_filtered_callbacks(self, row: int) -> dict:
        """Map filtered row index to actual document and get callbacks."""
        doc = self._filtered_docs[row]
        actual_row = self.documents.index(doc)
        return self.get_action_callbacks(actual_row)

    def _apply_search_filter(self):
        """Re-render table when search text changes."""
        if self.documents:
            self._populate_table()

    # ------------------------------------------------------------------
    # Overridable
    # ------------------------------------------------------------------

    def fetch_documents(self) -> list:
        """Subclasses must implement: return list of document dicts from API."""
        raise NotImplementedError

    def get_action_callbacks(self, row: int) -> dict:
        """Subclasses must implement: return dict of action callbacks for a row."""
        raise NotImplementedError

    def _empty_state_message(self) -> str:
        """Override to customise the empty-state text."""
        return "No documents found."

    # ------------------------------------------------------------------
    # Shared Actions
    # ------------------------------------------------------------------

    def view_document(self, row):
        """View document — opens secure viewer for confidential, regular for others."""
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()

        if classification == 'confidential':
            response = QMessageBox.warning(
                self,
                "Security Monitoring Active",
                "This is a CONFIDENTIAL document.\n\n"
                "Security monitoring will be active:\n"
                "• Your camera will monitor for your presence\n"
                "• The screen will block if you leave\n"
                "• Cell phone detection will trigger alerts\n"
                "• All events will be logged\n\n"
                "Do you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if response != QMessageBox.StandardButton.Yes:
                return

        try:
            file_content = self.api_client.view_document(doc['id'])
            if file_content:
                if classification == 'confidential':
                    viewer = SecureDocumentViewer(doc, file_content, self.api_client, self)
                else:
                    viewer = DocumentViewer(doc, file_content, self)
                viewer.exec()
            else:
                QMessageBox.warning(self, "Error", "Failed to load document for viewing.")
        except Exception as e:
            QMessageBox.critical(self, "View Failed", f"Could not view document: {e}")

    def download_document(self, row):
        doc = self.documents[row]
        filename = doc.get('filename', 'downloaded_file')
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Document", filename)
        if save_path:
            try:
                self.api_client.download_document(doc['id'], save_path)
                QMessageBox.information(self, "Success", f"Document '{filename}' downloaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Download Failed", f"Could not download document: {e}")

    def delete_document(self, row):
        doc = self.documents[row]
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete '{doc.get('filename')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_document(doc['id'])
                QMessageBox.information(self, "Success", "Document deleted successfully.")
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "Deletion Failed", f"Could not delete document: {e}")

    def refresh_data(self):
        """Called by MainWindow when this view is navigated to."""
        self.load_documents()
