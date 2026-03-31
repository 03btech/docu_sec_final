"""
Classification Correction Dialog
Allows document owners to manually override the AI classification and department tags.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QScrollArea, QWidget, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
import qtawesome as qta


class ClassificationDialog(QDialog):
    """Modal dialog for manually changing a document's classification level and department tags.

    Returns the selected classification string via self.selected_classification 
    and list of department IDs via self.selected_departments after accept().
    """

    CLASSIFICATIONS = [
        ("public", "Public", "#10b981", "Safe for external audiences"),
        ("internal", "Internal", "#3b82f6", "Employees / staff only"),
        ("confidential", "Confidential", "#ef4444", "Restricted — explicit access only"),
    ]

    def __init__(self, document: dict, api_client, parent=None):
        super().__init__(parent)
        self.document = document
        self.api_client = api_client
        self.selected_classification = None
        self.selected_departments = []
        self.checkboxes = []  # Keep track of QCheckBox widgets
        
        self.setWindowTitle("Edit Document Metadata")
        self.setFixedSize(450, 500)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_label = QLabel("Edit Metadata")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #1f2937;
            }
        """)
        layout.addWidget(header_label)

        # Document name
        filename = self.document.get('filename', 'Unknown')
        doc_label = QLabel(f"Document: {filename}")
        doc_label.setStyleSheet("QLabel { font-size: 13px; color: #6b7280; }")
        doc_label.setWordWrap(True)
        layout.addWidget(doc_label)

        # Current classification
        current = self.document.get('classification', 'unclassified')
        source = self.document.get('classification_source', 'ai')
        source_text = "AI" if source == "ai" else "Manual"
        current_label = QLabel(f"Current Level: {current.upper()}  (set by {source_text})")
        current_label.setStyleSheet("QLabel { font-size: 12px; color: #9ca3af; }")
        layout.addWidget(current_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #e5e7eb; }")
        layout.addWidget(separator)

        # Classification selector
        selector_label = QLabel("Security Level:")
        selector_label.setStyleSheet("QLabel { font-size: 14px; font-weight: 500; color: #374151; }")
        layout.addWidget(selector_label)

        self.combo = QComboBox()
        self.combo.setStyleSheet("""
            QComboBox {
                padding: 10px 14px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
                selection-background-color: #f3f4f6;
                selection-color: #1f2937;
            }
        """)

        current_index = 0
        for i, (value, label, color, description) in enumerate(self.CLASSIFICATIONS):
            self.combo.addItem(f"  {label} — {description}", value)
            if value == current:
                current_index = i
        self.combo.setCurrentIndex(current_index)
        layout.addWidget(self.combo)

        # Spacer
        layout.addSpacing(8)

        # Departments section
        dept_label = QLabel("Relevant Departments (Max 5):")
        dept_label.setStyleSheet("QLabel { font-size: 14px; font-weight: 500; color: #374151; }")
        layout.addWidget(dept_label)

        # Scroll area for departments
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background-color: #f9fafb;
            }
            QScrollBar:vertical {
                border: none;
                background: #f3f4f6;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(8)

        # Current department IDs
        current_depts = [d.get('department_id') for d in self.document.get('departments', [])]
        
        # Fetch departments from API
        try:
            departments = self.api_client.get_departments()
            for dept in departments:
                cb = QCheckBox(dept['name'])
                cb.setProperty("dept_id", dept['id'])
                cb.setStyleSheet("""
                    QCheckBox {
                        font-size: 13px;
                        color: #4b5563;
                        padding: 2px;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                        border-radius: 4px;
                        border: 1px solid #d1d5db;
                        background-color: white;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #3b82f6;
                        border: 1px solid #3b82f6;
                        image: url(check.png); /* Fallback */
                    }
                """)
                # Mark as checked if currently tagged
                if dept['id'] in current_depts:
                    cb.setChecked(True)
                
                # Connect signal to enforce max 5 limit
                cb.toggled.connect(self._on_dept_toggled)
                
                scroll_layout.addWidget(cb)
                self.checkboxes.append(cb)
        except Exception as e:
            error_lbl = QLabel(f"Could not load departments: {e}")
            error_lbl.setStyleSheet("color: red;")
            scroll_layout.addWidget(error_lbl)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        layout.addStretch()

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
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_dept_toggled(self, checked):
        """Enforce maximum limit of 5 departments."""
        if checked:
            checked_count = sum(1 for cb in self.checkboxes if cb.isChecked())
            if checked_count > 5:
                # Uncheck the box that triggered this
                sender = self.sender()
                sender.setChecked(False)
                QMessageBox.warning(self, "Limit Reached", "You can select a maximum of 5 departments.")

    def _on_save(self):
        self.selected_classification = self.combo.currentData()
        self.selected_departments = [
            cb.property("dept_id") for cb in self.checkboxes if cb.isChecked()
        ]
        self.accept()
