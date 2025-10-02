"""
Modern Document Card Table with Action Menu
Implements clean UI/UX with hidden actions in dropdown menu
"""
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, 
    QHBoxLayout, QWidget, QMenu, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor
import qtawesome as qta


class ClassificationBadge(QWidget):
    """Custom widget for classification badges with color coding"""
    
    CLASSIFICATION_COLORS = {
        'public': ('#10b981', '#d1fae5'),      # Green
        'internal': ('#3b82f6', '#dbeafe'),    # Blue
        'confidential': ('#ef4444', '#fee2e2'), # Red
        'unclassified': ('#6b7280', '#f3f4f6')  # Gray
    }
    
    def __init__(self, classification: str, parent=None):
        super().__init__(parent)
        self.classification = classification.lower()
        self.setMinimumHeight(40)  # Ensure minimum height
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No padding
        
        # Get colors for classification
        text_color, bg_color = self.CLASSIFICATION_COLORS.get(
            self.classification, 
            self.CLASSIFICATION_COLORS['unclassified']
        )
        
        # Create badge label
        badge = QLabel(self.classification.upper())
        badge.setMinimumHeight(24)  # Ensure minimum height for badge
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        
        layout.addWidget(badge)
        layout.addStretch()


class ActionMenuButton(QPushButton):
    """Custom button that shows a dropdown menu with actions"""
    
    def __init__(self, actions: dict, row: int, parent=None):
        super().__init__(parent)
        self.action_callbacks = actions  # Store as different name to avoid conflict
        self.row = row
        self.setup_ui()
    
    def setup_ui(self):
        # Set icon - three vertical dots
        self.setIcon(qta.icon('fa5s.ellipsis-v', color='#6b7280'))
        self.setIconSize(QSize(18, 18))
        self.setToolTip("More actions")
        
        # Style the button
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 18px;
                padding: 8px 14px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
            QPushButton:pressed {
                background-color: #e5e7eb;
            }
        """)
        
        # Connect to show menu
        self.clicked.connect(self.show_menu)
    
    def show_menu(self):
        """Show dropdown menu with available actions"""
        menu = QMenu(self)
        
        # Style the menu
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px 8px 40px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
            QMenu::icon {
                left: 12px;
            }
        """)
        
        # Add actions to menu
        if 'view' in self.action_callbacks:
            view_action = menu.addAction(
                qta.icon('fa5s.eye', color='#3b82f6'), 
                "View Document"
            )
            view_action.triggered.connect(lambda: self.action_callbacks['view'](self.row))
        
        if 'download' in self.action_callbacks:
            download_action = menu.addAction(
                qta.icon('fa5s.download', color='#10b981'), 
                "Download"
            )
            download_action.triggered.connect(lambda: self.action_callbacks['download'](self.row))
        
        if 'share' in self.action_callbacks:
            menu.addSeparator()
            share_action = menu.addAction(
                qta.icon('fa5s.share-alt', color='#f59e0b'), 
                "Share"
            )
            share_action.triggered.connect(lambda: self.action_callbacks['share'](self.row))
        
        if 'manage_sharing' in self.action_callbacks:
            manage_action = menu.addAction(
                qta.icon('fa5s.users-cog', color='#8b5cf6'), 
                "Manage Sharing"
            )
            manage_action.triggered.connect(lambda: self.action_callbacks['manage_sharing'](self.row))
        
        if 'delete' in self.action_callbacks:
            if menu.actions():  # Only add separator if there are other actions
                menu.addSeparator()
            delete_action = menu.addAction(
                qta.icon('fa5s.trash-alt', color='#ef4444'), 
                "Delete"
            )
            delete_action.triggered.connect(lambda: self.action_callbacks['delete'](self.row))
        
        # Show menu at button position
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))


class ModernDocumentTable(QTableWidget):
    """
    Modern document table with card-like design and hidden action menu.
    Follows best UI/UX practices with clean, minimal interface.
    """
    
    def __init__(self, headers=None, parent=None):
        super().__init__(parent)
        
        # Default headers if none provided
        if headers is None:
            headers = ["Document", "Classification", "Owner", "Upload Date", ""]
        
        self.headers = headers
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize table UI with modern styling"""
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        
        # Hide row numbers
        vertical_header = self.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        
        # Set table properties
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)  # We'll use custom row styling
        self.setShowGrid(False)
        
        # Set fixed row height - not adjustable by user
        v_header = self.verticalHeader()
        if v_header:
            v_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            v_header.setDefaultSectionSize(60)
        
        # Configure column behavior
        header = self.horizontalHeader()
        if header:
            # Document name - stretch
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            # Classification - fixed width
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(1, 150)
            # Owner - interactive
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            self.setColumnWidth(2, 150)
            # Date - interactive
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.setColumnWidth(3, 120)
            # Actions - fixed width
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(4, 60)
        
        # Apply modern styling
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 0px;
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
                letter-spacing: 0.5px;
            }
        """)
    
    def set_documents(self, documents: list, action_callbacks: dict):
        """
        Populate table with documents and action callbacks.
        
        Args:
            documents: List of document dictionaries
            action_callbacks: Dict mapping action names to callback functions
        """
        self.setRowCount(len(documents))
        
        for row, doc in enumerate(documents):
            # Set row height explicitly for each row
            self.setRowHeight(row, 60)
            
            # Column 0: Document name with file icon
            doc_widget = self._create_document_cell(doc)
            self.setCellWidget(row, 0, doc_widget)
            
            # Column 1: Classification badge
            classification = doc.get('classification', 'unclassified')
            badge_widget = ClassificationBadge(classification)
            self.setCellWidget(row, 1, badge_widget)
            
            # Column 2: Owner
            owner = doc.get('owner')
            owner_text = ''
            if owner and isinstance(owner, dict):
                owner_text = owner.get('username', '')
            elif owner:
                owner_text = str(owner)
            
            owner_item = QTableWidgetItem(owner_text)
            owner_item.setForeground(QColor('#6b7280'))
            owner_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 2, owner_item)
            
            # Column 3: Date
            date_str = doc.get('upload_date', '')
            if date_str:
                date_str = date_str.split('T')[0]
            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor('#6b7280'))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 3, date_item)
            
            # Column 4: Action menu button
            action_button = ActionMenuButton(action_callbacks, row)
            
            # Center the button in cell
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(action_button)
            button_layout.addStretch()
            
            self.setCellWidget(row, 4, button_container)
    
    def set_documents_with_row_callbacks(self, documents: list, callback_getter):
        """
        Populate table with documents and per-row action callbacks.
        
        Args:
            documents: List of document dictionaries
            callback_getter: Function that takes row index and returns action callbacks dict
        """
        self.setRowCount(len(documents))
        
        for row, doc in enumerate(documents):
            # Set row height explicitly for each row
            self.setRowHeight(row, 60)
            
            # Column 0: Document name with file icon
            doc_widget = self._create_document_cell(doc)
            self.setCellWidget(row, 0, doc_widget)
            
            # Column 1: Classification badge
            classification = doc.get('classification', 'unclassified')
            badge_widget = ClassificationBadge(classification)
            self.setCellWidget(row, 1, badge_widget)
            
            # Column 2: Owner
            owner = doc.get('owner')
            owner_text = ''
            if owner and isinstance(owner, dict):
                owner_text = owner.get('username', '')
            elif owner:
                owner_text = str(owner)
            
            owner_item = QTableWidgetItem(owner_text)
            owner_item.setForeground(QColor('#6b7280'))
            owner_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 2, owner_item)
            
            # Column 3: Date
            date_str = doc.get('upload_date', '')
            if date_str:
                date_str = date_str.split('T')[0]
            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor('#6b7280'))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 3, date_item)
            
            # Column 4: Action menu button with row-specific callbacks
            action_callbacks = callback_getter(row)
            action_button = ActionMenuButton(action_callbacks, row)
            
            # Center the button in cell
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(action_button)
            button_layout.addStretch()
            
            self.setCellWidget(row, 4, button_container)
    
    def _create_document_cell(self, doc: dict) -> QWidget:
        """Create a widget for document name with icon"""
        widget = QWidget()
        widget.setMinimumHeight(50)  # Ensure minimum height
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)  # Minimal horizontal padding only
        layout.setSpacing(12)
        
        # File icon based on extension
        filename = doc.get('filename', '')
        file_icon = self._get_file_icon(filename)
        
        icon_label = QLabel()
        icon_label.setPixmap(file_icon.pixmap(QSize(28, 28)))  # Larger icon
        icon_label.setFixedSize(28, 28)
        layout.addWidget(icon_label)
        
        # File name label
        name_label = QLabel(filename)
        name_label.setStyleSheet("""
            QLabel {
                color: #0f1016;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        name_label.setMinimumHeight(30)
        layout.addWidget(name_label)
        layout.addStretch()
        
        return widget
    
    def _get_file_icon(self, filename: str):
        """Get appropriate icon based on file extension"""
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        
        icon_map = {
            'pdf': ('fa5s.file-pdf', '#ef4444'),
            'doc': ('fa5s.file-word', '#3b82f6'),
            'docx': ('fa5s.file-word', '#3b82f6'),
            'xls': ('fa5s.file-excel', '#10b981'),
            'xlsx': ('fa5s.file-excel', '#10b981'),
            'ppt': ('fa5s.file-powerpoint', '#f59e0b'),
            'pptx': ('fa5s.file-powerpoint', '#f59e0b'),
            'txt': ('fa5s.file-alt', '#6b7280'),
            'jpg': ('fa5s.file-image', '#8b5cf6'),
            'jpeg': ('fa5s.file-image', '#8b5cf6'),
            'png': ('fa5s.file-image', '#8b5cf6'),
            'zip': ('fa5s.file-archive', '#f59e0b'),
            'rar': ('fa5s.file-archive', '#f59e0b'),
        }
        
        icon_name, color = icon_map.get(extension, ('fa5s.file', '#6b7280'))
        return qta.icon(icon_name, color=color)
