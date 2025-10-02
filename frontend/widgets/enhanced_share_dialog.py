"""
Enhanced Share Document Dialog with User Search
Allows sharing confidential documents with user autocomplete
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QMessageBox, QLineEdit, QListWidget, QListWidgetItem,
    QWidget, QCompleter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import APIClient
import qtawesome as qta


class UserSearchWidget(QWidget):
    """Widget for searching and selecting users"""
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.selected_user = None
        self.users_cache = []
        self.setup_ui()
        self.load_users()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, username, or email...")
        self.search_input.setStyleSheet("""
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
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(200)
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f3f4f6;
            }
            QListWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
            }
            QListWidget::item:hover {
                background-color: #f9fafb;
            }
        """)
        self.results_list.itemClicked.connect(self.on_user_selected)
        layout.addWidget(self.results_list)
        
        # Selected user display
        self.selected_label = QLabel("No user selected")
        self.selected_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
                padding: 8px;
                background-color: #f9fafb;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.selected_label)
    
    def load_users(self):
        """Load all users from API"""
        try:
            self.users_cache = self.api_client.get_users()
            self.populate_list(self.users_cache)
        except Exception as e:
            print(f"Failed to load users: {e}")
    
    def on_search_changed(self, text):
        """Filter users based on search text"""
        if not text:
            self.populate_list(self.users_cache)
            return
        
        text_lower = text.lower()
        filtered = [
            user for user in self.users_cache
            if (text_lower in user.get('username', '').lower() or
                text_lower in user.get('first_name', '').lower() or
                text_lower in user.get('last_name', '').lower() or
                text_lower in user.get('email', '').lower())
        ]
        self.populate_list(filtered)
    
    def populate_list(self, users):
        """Populate the list widget with users"""
        self.results_list.clear()
        for user in users:
            item_text = f"{user.get('first_name', '')} {user.get('last_name', '')} (@{user.get('username', '')}) - {user.get('email', '')}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, user)
            self.results_list.addItem(item)
    
    def on_user_selected(self, item):
        """Handle user selection"""
        self.selected_user = item.data(Qt.ItemDataRole.UserRole)
        self.selected_label.setText(
            f"✓ Selected: {self.selected_user.get('first_name', '')} "
            f"{self.selected_user.get('last_name', '')} (@{self.selected_user.get('username', '')})"
        )
        self.selected_label.setStyleSheet("""
            QLabel {
                color: #059669;
                font-size: 13px;
                font-weight: 500;
                padding: 8px;
                background-color: #d1fae5;
                border-radius: 6px;
            }
        """)
    
    def get_selected_user(self):
        """Get the currently selected user"""
        return self.selected_user


class EnhancedShareDialog(QDialog):
    """Enhanced dialog for sharing documents with user search"""
    
    def __init__(self, document: dict, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.document = document
        self.api_client = api_client
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Share Document")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
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
        user_label = QLabel("Select user to share with:")
        user_label.setStyleSheet("font-weight: 500; color: #374151; font-size: 14px;")
        layout.addWidget(user_label)
        
        # User search widget
        self.user_search = UserSearchWidget(self.api_client)
        layout.addWidget(self.user_search)
        
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
    
    def share_document(self):
        """Share the document with the selected user"""
        selected_user = self.user_search.get_selected_user()
        
        if not selected_user:
            QMessageBox.warning(
                self,
                "No User Selected",
                "Please select a user to share the document with."
            )
            return
        
        permission = self.permission_combo.currentText()
        
        try:
            # Call API to share document
            success = self.api_client.share_document(
                self.document['id'],
                selected_user['id'],
                permission
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Document shared successfully with {selected_user['first_name']} "
                    f"{selected_user['last_name']}!"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Share Failed",
                    "Failed to share document. The document may already be shared with this user."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while sharing: {str(e)}"
            )
