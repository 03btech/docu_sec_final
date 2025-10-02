from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from api.client import APIClient
from widgets.document_card_table import ModernDocumentTable
from widgets.enhanced_share_dialog import EnhancedShareDialog
from widgets.manage_sharing_dialog import ManageSharingDialog
from .document_viewer import DocumentViewer
from .secure_document_viewer import SecureDocumentViewer
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.camera_utils import check_camera_available

class MyDocumentsView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.documents = []
        self.setup_ui()
        self.load_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)

        # Header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Title
        title = QLabel("My Documents")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #0f1016;
            }
        """)
        header_layout.addWidget(title)
        
        # Description
        description = QLabel("Documents you own and have uploaded to the system")
        description.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6b7280;
            }
        """)
        header_layout.addWidget(description)
        
        layout.addWidget(header_widget)

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
        action_bar.addStretch()
        
        layout.addLayout(action_bar)

        # Modern document table
        self.table = ModernDocumentTable()
        layout.addWidget(self.table)

    def load_documents(self):
        try:
            # Assuming get_my_documents returns documents owned by the current user
            self.documents = self.api_client.get_my_documents()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load your documents: {str(e)}")

    def populate_table(self):
        # Pass the method to get action callbacks per row
        self.table.set_documents_with_row_callbacks(self.documents, self.get_action_callbacks)
    
    def view_document(self, row):
        """View document in secure viewer."""
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()
        
        print(f"\n=== FRONTEND VIEW DEBUG ===")
        print(f"Document: {doc.get('filename')}")
        print(f"Document ID: {doc.get('id')}")
        print(f"Classification: {classification}")
        print(f"Owner: {doc.get('owner')}")
        
        # Check if confidential - require camera
        if classification == 'confidential':
            print("⚠️ Confidential document - checking camera...")
            
            # Check camera availability
            camera_available, camera_message = check_camera_available()
            
            if not camera_available:
                QMessageBox.critical(
                    self, 
                    "Camera Required", 
                    f"Cannot view confidential documents without an active camera.\n\n{camera_message}"
                )
                print(f"❌ Camera check failed: {camera_message}")
                return
            
            print(f"✅ Camera available: {camera_message}")
            
            # Show security warning
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
                print("❌ User declined to proceed with monitoring")
                return
        
        try:
            # Get document content
            print(f"Calling API: view_document({doc['id']})")
            file_content = self.api_client.view_document(doc['id'])
            
            if file_content:
                print(f"✅ File content received: {len(file_content)} bytes")
                print(f"Opening document viewer...")
                
                # Use secure viewer for confidential, regular for others
                if classification == 'confidential':
                    viewer = SecureDocumentViewer(doc, file_content, self.api_client, self)
                else:
                    viewer = DocumentViewer(doc, file_content, self)
                    
                viewer.exec()
                print(f"Viewer closed")
            else:
                print(f"❌ No file content received")
                QMessageBox.warning(self, "Error", "Failed to load document for viewing.")
        except Exception as e:
            print(f"❌ Exception occurred: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "View Failed", f"Could not view document: {e}")
        
        print(f"=== END FRONTEND DEBUG ===\n")

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
        confirm = QMessageBox.question(self, "Confirm Deletion", 
                                       f"Are you sure you want to delete '{doc.get('filename')}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_document(doc['id'])
                QMessageBox.information(self, "Success", "Document deleted successfully.")
                self.load_documents() # Refresh
            except Exception as e:
                QMessageBox.critical(self, "Deletion Failed", f"Could not delete document: {e}")

    def get_action_callbacks(self, row: int) -> dict:
        """Get action callbacks for a specific row based on document classification"""
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()
        
        # Base actions available to all documents
        action_callbacks = {
            'view': self.view_document,
            'delete': self.delete_document
        }
        
        # Only confidential documents can be shared
        if classification == 'confidential':
            action_callbacks['share'] = self.share_document
            action_callbacks['manage_sharing'] = self.manage_sharing
        
        # Download available for non-confidential documents only
        if classification != 'confidential':
            action_callbacks['download'] = self.download_document
        
        return action_callbacks
    
    def share_document(self, row):
        """Open share dialog for confidential documents"""
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()
        
        # Double check that this is a confidential document
        if classification != 'confidential':
            QMessageBox.warning(
                self,
                "Not Allowed",
                "Only confidential documents can be shared with other users."
            )
            return
        
        # Open share dialog
        dialog = EnhancedShareDialog(doc, self.api_client, self)
        dialog.exec()
    
    def manage_sharing(self, row):
        """Open manage sharing dialog for confidential documents"""
        doc = self.documents[row]
        
        # Open manage sharing dialog
        dialog = ManageSharingDialog(doc, self.api_client, self)
        dialog.exec()

    def refresh_data(self):
        """Refresh the documents list."""
        self.load_documents()
