"""
Manage Document Sharing Dialog
View and manage who has access to a document
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QWidget, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from api.client import APIClient
import qtawesome as qta


class ManageSharingDialog(QDialog):
    """Dialog for managing document sharing permissions"""
    
    def __init__(self, document: dict, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.document = document
        self.api_client = api_client
        self.permissions = []
        self.setup_ui()
        self.load_permissions()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Manage Document Sharing")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel(f"Sharing: {self.document.get('filename', 'Document')}")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #0f1016;
            }
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Manage who has access to this document")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6b7280;
            }
        """)
        header_layout.addWidget(subtitle)
        
        # Divider
        divider = QWidget()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: #e5e7eb;")
        header_layout.addWidget(divider)
        
        layout.addLayout(header_layout)
        
        # Permissions table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["User", "Email", "Permission", "Actions"])
        
        # Configure table
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        
        v_header = self.table.verticalHeader()
        if v_header:
            v_header.setVisible(False)
        
        # Column widths
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 200)  # User name
            self.table.setColumnWidth(2, 180)  # Permission dropdown - increased
            self.table.setColumnWidth(3, 180)  # Actions button - increased
        
        # Table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget::item:selected {
                background-color: #f9fafb;
                color: #0f1016;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                color: #6b7280;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #e5e7eb;
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)
        
        layout.addWidget(self.table)
        
        # Info label
        self.info_label = QLabel("Loading permissions...")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync-alt', color='#3b82f6'))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #3b82f6;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #eff6ff;
            }
        """)
        refresh_btn.clicked.connect(self.load_permissions)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
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
        """)
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)
    
    def load_permissions(self):
        """Load permissions from API"""
        try:
            self.permissions = self.api_client.get_document_permissions(self.document['id'])
            self.populate_table()
            
            if self.permissions:
                self.info_label.setText(f"Shared with {len(self.permissions)} user(s)")
            else:
                self.info_label.setText("This document is not shared with anyone yet")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load permissions: {str(e)}"
            )
            self.info_label.setText("Error loading permissions")
    
    def populate_table(self):
        """Populate the table with permissions"""
        self.table.setRowCount(len(self.permissions))
        
        for row, perm in enumerate(self.permissions):
            user = perm.get('user', {})
            
            # User name
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor('#0f1016'))
            self.table.setItem(row, 0, name_item)
            
            # Email
            email = user.get('email', '')
            email_item = QTableWidgetItem(email)
            email_item.setForeground(QColor('#6b7280'))
            self.table.setItem(row, 1, email_item)
            
            # Permission dropdown
            permission_widget = QWidget()
            permission_layout = QHBoxLayout(permission_widget)
            permission_layout.setContentsMargins(10, 8, 10, 8)
            permission_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            permission_combo = QComboBox()
            permission_combo.addItems(["view", "edit"])
            permission_combo.setCurrentText(perm.get('permission', 'view'))
            permission_combo.setFixedSize(140, 36)  # Fixed size to fit in column
            permission_combo.setStyleSheet("""
                QComboBox {
                    padding: 8px 12px;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    font-size: 14px;
                    background-color: white;
                }
                QComboBox:hover {
                    border-color: #9ca3af;
                }
                QComboBox::drop-down {
                    width: 24px;
                }
            """)
            permission_combo.currentTextChanged.connect(
                lambda text, p=perm: self.update_permission(p, text)
            )
            permission_layout.addWidget(permission_combo)
            
            self.table.setCellWidget(row, 2, permission_widget)
            
            # Actions buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(10, 8, 10, 8)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            revoke_btn = QPushButton("Revoke")
            revoke_btn.setIcon(qta.icon('fa5s.times', color='#ef4444'))
            revoke_btn.setFixedSize(140, 36)  # Fixed size to fit in column
            revoke_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fee2e2;
                    color: #dc2626;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #fecaca;
                }
                QPushButton:pressed {
                    background-color: #fca5a5;
                }
            """)
            revoke_btn.clicked.connect(lambda checked, p=perm: self.revoke_permission(p))
            actions_layout.addWidget(revoke_btn)
            
            self.table.setCellWidget(row, 3, actions_widget)
            
            # Set row height - increased for better spacing
            self.table.setRowHeight(row, 80)
    
    def update_permission(self, permission: dict, new_level: str):
        """Update permission level"""
        if new_level == permission.get('permission'):
            return  # No change
        
        try:
            success = self.api_client.update_permission(
                self.document['id'],
                permission['id'],
                new_level
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Permission updated to '{new_level}'"
                )
                self.load_permissions()  # Refresh
            else:
                QMessageBox.critical(
                    self,
                    "Update Failed",
                    "Failed to update permission level"
                )
                self.load_permissions()  # Reset to original
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error updating permission: {str(e)}"
            )
    
    def revoke_permission(self, permission: dict):
        """Revoke a user's permission"""
        user = permission.get('user', {})
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        
        reply = QMessageBox.question(
            self,
            "Confirm Revoke",
            f"Are you sure you want to revoke access for {user_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.api_client.revoke_permission(
                    self.document['id'],
                    permission['id']
                )
                
                if success:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Access revoked for {user_name}"
                    )
                    self.load_permissions()  # Refresh
                else:
                    QMessageBox.critical(
                        self,
                        "Revoke Failed",
                        "Failed to revoke permission"
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error revoking permission: {str(e)}"
                )
