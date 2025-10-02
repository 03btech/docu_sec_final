"""
Share Document Dialog
Allows sharing confidential documents with other users
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from api.client import APIClient
import qtawesome as qta


class ShareDocumentDialog(QDialog):
    """Dialog for sharing a document with another user"""
    
    def __init__(self, document: dict, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.document = document
        self.api_client = api_client
        self.users = []
        self.setup_ui()
        self.load_users()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Share Document")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Document info header
        header = QLabel(f"Share: {self.document.get('filename', 'Document')}")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #0f1016;
                padding-bottom: 8px;
                border-bottom: 2px solid #e5e7eb;
            }
        """)
        layout.addWidget(header)
        
        # Classification badge
        classification = self.document.get('classification', 'unclassified').upper()
        classification_label = QLabel(f"Classification: {classification}")
        classification_label.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        layout.addWidget(classification_label)
        
        # Warning message
        warning = QLabel(
            "⚠️ You are sharing a CONFIDENTIAL document. "
            "Only share with authorized users."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("""
            QLabel {
                background-color: #fef2f2;
                color: #991b1b;
                padding: 12px;
                border-radius: 8px;
                border-left: 4px solid #ef4444;
            }
        """)
        layout.addWidget(warning)
        
        # User selection
        user_label = QLabel("Share with user:")
        user_label.setStyleSheet("font-weight: 500; color: #374151;")
        layout.addWidget(user_label)
        
        # User input - can be username or user ID
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter username or user ID")
        self.user_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                outline: none;
            }
        """)
        layout.addWidget(self.user_input)
        
        # Permission selection
        permission_label = QLabel("Permission level:")
        permission_label.setStyleSheet("font-weight: 500; color: #374151; margin-top: 8px;")
        layout.addWidget(permission_label)
        
        self.permission_combo = QComboBox()
        self.permission_combo.addItems(["view", "edit"])
        self.permission_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #9ca3af;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6b7280;
                margin-right: 10px;
            }
        """)
        layout.addWidget(self.permission_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        share_btn = QPushButton("Share Document")
        share_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        share_btn.clicked.connect(self.share_document)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(share_btn)
        
        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)
    
    def load_users(self):
        """Load available users from backend"""
        # Note: This would need a backend endpoint to list users
        # For now, we'll use manual input
        pass
    
    def share_document(self):
        """Share the document with the selected user"""
        user_input = self.user_input.text().strip()
        
        if not user_input:
            QMessageBox.warning(
                self,
                "Input Required",
                "Please enter a username or user ID to share with."
            )
            return
        
        permission = self.permission_combo.currentText()
        
        try:
            # Try to convert to int (user ID), otherwise treat as username
            try:
                user_id = int(user_input)
            except ValueError:
                # If not a number, we need to look up the username
                # For now, show an error asking for user ID
                QMessageBox.warning(
                    self,
                    "User ID Required",
                    "Please enter a numeric user ID.\n\n"
                    "Username lookup is not yet implemented."
                )
                return
            
            # Call API to share document
            success = self.api_client.share_document(
                self.document['id'],
                user_id,
                permission
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Document shared successfully with user ID {user_id}!"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Share Failed",
                    "Failed to share document. The user may not exist or you may not have permission."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while sharing: {str(e)}"
            )
