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
    """Custom widget for classification badges with color coding.
    
    Handles classification_status from the async classification pipeline:
    - queued/extracting_text/classifying → "Classifying..." dimmed badge
    - failed → "Failed" red badge with tooltip from classification_error
    - completed + unclassified → "Needs Review" amber badge
    - completed → normal classification badge
    """
    
    CLASSIFICATION_COLORS = {
        'public': ('#10b981', '#d1fae5'),      # Green
        'internal': ('#3b82f6', '#dbeafe'),    # Blue
        'confidential': ('#ef4444', '#fee2e2'), # Red
        'unclassified': ('#6b7280', '#f3f4f6')  # Gray
    }

    # Status colors for non-completed classification states
    STATUS_COLORS = {
        'classifying': ('#6b7280', '#f3f4f6'),    # Gray dimmed
        'failed': ('#dc2626', '#fef2f2'),          # Red
        'needs_review': ('#d97706', '#fffbeb'),    # Amber
    }
    
    def __init__(self, classification: str, classification_status: str = 'completed',
                 classification_error: str = '', parent=None):
        super().__init__(parent)
        self.classification = classification.lower()
        self.classification_status = classification_status or 'completed'
        self.classification_error = classification_error or ''
        self.setMinimumHeight(40)  # Ensure minimum height
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No padding
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Determine badge text and colors based on classification_status
        badge_text, text_color, bg_color, tooltip = self._resolve_badge()
        
        # Create badge label
        badge = QLabel(badge_text)
        badge.setMinimumHeight(24)  # Ensure minimum height for badge
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        if tooltip:
            badge.setToolTip(tooltip)
        
        layout.addStretch()
        layout.addWidget(badge)
        layout.addStretch()

    def _resolve_badge(self) -> tuple:
        """Resolve badge text, colors, and tooltip based on classification status.
        
        Returns:
            (badge_text, text_color, bg_color, tooltip)
        """
        status = self.classification_status

        # In-progress states: queued, extracting_text, classifying
        if status in ('queued', 'extracting_text', 'classifying'):
            text_color, bg_color = self.STATUS_COLORS['classifying']
            return ('CLASSIFYING...', text_color, bg_color, 'Classification in progress')

        # Failed state
        if status == 'failed':
            text_color, bg_color = self.STATUS_COLORS['failed']
            tooltip = self.classification_error if self.classification_error else 'Classification failed'
            return ('FAILED', text_color, bg_color, tooltip)

        # Completed but unclassified → needs review
        if status == 'completed' and self.classification == 'unclassified':
            text_color, bg_color = self.STATUS_COLORS['needs_review']
            return ('NEEDS REVIEW', text_color, bg_color, 'Classification completed but result is unclassified')

        # Normal completed state
        text_color, bg_color = self.CLASSIFICATION_COLORS.get(
            self.classification,
            self.CLASSIFICATION_COLORS['unclassified']
        )
        return (self.classification.upper(), text_color, bg_color, '')


class DepartmentBadges(QWidget):
    """Widget that renders 1-N department name pills in a horizontal flow.

    Shows compact colored badges for each AI-inferred department tag.
    If no departments: shows '—' in muted gray.
    If classification is in progress: shows 'Pending...' in gray.
    """

    BADGE_COLORS = [
        ('#0ea5e9', '#e0f2fe'),   # Sky blue
        ('#8b5cf6', '#ede9fe'),   # Violet
        ('#f97316', '#fff7ed'),   # Orange
        ('#14b8a6', '#ccfbf1'),   # Teal
        ('#ec4899', '#fce7f3'),   # Pink
        ('#64748b', '#f1f5f9'),   # Slate
    ]

    def __init__(self, departments: list, classification_status: str = 'completed', parent=None):
        super().__init__(parent)
        self.departments = departments or []
        self.classification_status = classification_status or 'completed'
        self.setMinimumHeight(40)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # In-progress states
        if self.classification_status in ('queued', 'extracting_text', 'classifying'):
            pending = QLabel('Pending...')
            pending.setStyleSheet("""
                QLabel {
                    color: #9ca3af;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            main_layout.addWidget(pending, alignment=Qt.AlignmentFlag.AlignHCenter)
            return

        # Extract valid department names and their original indices for color consistency
        valid_depts = []
        for i, dept in enumerate(self.departments):
            dept_name = dept.get('department_name', '') if isinstance(dept, dict) else str(dept)
            if dept_name:
                valid_depts.append((dept_name, i))

        # No valid departments tagged
        if not valid_depts:
            empty = QLabel('—')
            empty.setStyleSheet("""
                QLabel {
                    color: #d1d5db;
                    font-size: 13px;
                }
            """)
            main_layout.addWidget(empty, alignment=Qt.AlignmentFlag.AlignHCenter)
            return

        # Render department badges stacked 2 per row
        ITEMS_PER_ROW = 2
        for i in range(0, len(valid_depts), ITEMS_PER_ROW):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            
            row_depts = valid_depts[i:i+ITEMS_PER_ROW]
            for dept_name, original_idx in row_depts:
                text_color, bg_color = self.BADGE_COLORS[original_idx % len(self.BADGE_COLORS)]
                badge = QLabel(dept_name)
                badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: {bg_color};
                        color: {text_color};
                        border-radius: 10px;
                        padding: 5px 10px;
                        font-size: 9px;
                        font-weight: 600;
                    }}
                """)
                row_layout.addWidget(badge)
            
            main_layout.addLayout(row_layout)


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
        
        if 'retry' in self.action_callbacks:
            if menu.actions():
                menu.addSeparator()
            retry_action = menu.addAction(
                qta.icon('fa5s.redo', color='#f59e0b'),
                "Retry Classification"
            )
            retry_action.triggered.connect(lambda: self.action_callbacks['retry'](self.row))
        
        if 'change_classification' in self.action_callbacks:
            if menu.actions() and 'retry' not in self.action_callbacks:
                menu.addSeparator()
            change_action = menu.addAction(
                qta.icon('fa5s.tag', color='#6366f1'),
                "Change Classification"
            )
            change_action.triggered.connect(lambda: self.action_callbacks['change_classification'](self.row))
        
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
            headers = ["Document", "Security Level", "Relevant Depts.", "Owner", "Upload Date", ""]
        
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
            v_header.setDefaultSectionSize(75)
        
        # Configure column behavior
        header = self.horizontalHeader()
        if header:
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            # Document name - stretch
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            # Security Level - fixed width
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(1, 150)
            # Relevant Depts. - natural sizing for departments
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            # Owner - interactive
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.setColumnWidth(3, 150)
            # Date - interactive
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.setColumnWidth(4, 120)
            # Actions - fixed width
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(5, 60)
        
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
            self.setRowHeight(row, 75)
            
            # Column 0: Document name with file icon
            doc_widget = self._create_document_cell(doc)
            self.setCellWidget(row, 0, doc_widget)
            
            # Column 1: Classification badge (status-aware)
            classification = doc.get('classification', 'unclassified')
            classification_status = doc.get('classification_status', 'completed')
            classification_error = doc.get('classification_error', '')
            badge_widget = ClassificationBadge(
                classification, classification_status, classification_error
            )
            self.setCellWidget(row, 1, badge_widget)

            # Column 2: Department badges
            departments = doc.get('departments', [])
            dept_widget = DepartmentBadges(departments, classification_status)
            self.setCellWidget(row, 2, dept_widget)
            
            # Column 3: Owner
            owner = doc.get('owner')
            owner_text = ''
            if owner and isinstance(owner, dict):
                owner_text = owner.get('username', '')
            elif owner:
                owner_text = str(owner)
            
            owner_item = QTableWidgetItem(owner_text)
            owner_item.setForeground(QColor('#6b7280'))
            owner_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 3, owner_item)
            
            # Column 4: Date
            date_str = doc.get('upload_date', '')
            if date_str:
                date_str = date_str.split('T')[0]
            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor('#6b7280'))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 4, date_item)
            
            # Column 5: Action menu button
            action_button = ActionMenuButton(action_callbacks, row)
            
            # Center the button in cell
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(action_button)
            button_layout.addStretch()
            
            self.setCellWidget(row, 5, button_container)
    
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
            self.setRowHeight(row, 75)
            
            # Column 0: Document name with file icon
            doc_widget = self._create_document_cell(doc)
            self.setCellWidget(row, 0, doc_widget)
            
            # Column 1: Classification badge (status-aware)
            classification = doc.get('classification', 'unclassified')
            classification_status = doc.get('classification_status', 'completed')
            classification_error = doc.get('classification_error', '')
            badge_widget = ClassificationBadge(
                classification, classification_status, classification_error
            )
            self.setCellWidget(row, 1, badge_widget)

            # Column 2: Department badges
            departments = doc.get('departments', [])
            dept_widget = DepartmentBadges(departments, classification_status)
            self.setCellWidget(row, 2, dept_widget)
            
            # Column 3: Owner
            owner = doc.get('owner')
            owner_text = ''
            if owner and isinstance(owner, dict):
                owner_text = owner.get('username', '')
            elif owner:
                owner_text = str(owner)
            
            owner_item = QTableWidgetItem(owner_text)
            owner_item.setForeground(QColor('#6b7280'))
            owner_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 3, owner_item)
            
            # Column 4: Date
            date_str = doc.get('upload_date', '')
            if date_str:
                date_str = date_str.split('T')[0]
            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor('#6b7280'))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 4, date_item)
            
            # Column 5: Action menu button with row-specific callbacks
            action_callbacks = callback_getter(row)
            action_button = ActionMenuButton(action_callbacks, row)
            
            # Center the button in cell
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(action_button)
            button_layout.addStretch()
            
            self.setCellWidget(row, 5, button_container)
    
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
        
        layout.addStretch()
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
