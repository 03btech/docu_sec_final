"""
Access Logs View — Modern card-based layout with dynamic filters and action badges.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView,
                             QMessageBox, QComboBox, QLineEdit, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor
import qtawesome as qta
from api.client import APIClient
from datetime import datetime

# Normalise compound backend actions like "share_with_user_5" → "share"
_ACTION_NORMALIZE = {
    "view": "view",
    "download": "download",
    "edit_metadata": "edit",
    "delete": "delete",
}

def _normalise_action(raw: str) -> str:
    if raw in _ACTION_NORMALIZE:
        return _ACTION_NORMALIZE[raw]
    if raw.startswith("share_with_user"):
        return "share"
    if raw.startswith("revoke_permission"):
        return "revoke"
    if raw.startswith("update_permission"):
        return "update_permission"
    if raw == "upload":
        return "upload"
    return raw

_ACTION_STYLE: dict[str, tuple[str, str, str]] = {
    # action → (icon, text_color, bg_color)
    "view":              ("fa5s.eye",           "#2563eb", "#dbeafe"),
    "download":          ("fa5s.download",      "#0891b2", "#cffafe"),
    "upload":            ("fa5s.cloud-upload-alt","#16a34a","#dcfce7"),
    "edit":              ("fa5s.edit",           "#d97706", "#fef3c7"),
    "delete":            ("fa5s.trash-alt",      "#dc2626", "#fee2e2"),
    "share":             ("fa5s.share-alt",      "#7c3aed", "#ede9fe"),
    "revoke":            ("fa5s.user-slash",     "#9f1239", "#ffe4e6"),
    "update_permission": ("fa5s.user-edit",      "#0369a1", "#e0f2fe"),
}


class AccessLogsView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.logs: list[dict] = []
        self.setup_ui()

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        title = QLabel("Access Logs")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)

        desc = QLabel("Track all document access, sharing, and modification activities")
        desc.setStyleSheet("font-size: 14px; color: #6b7280; margin-bottom: 4px;")
        layout.addWidget(desc)

        # ── Filters Card ──
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
        """)
        fc_layout = QHBoxLayout(filter_card)
        fc_layout.setContentsMargins(16, 12, 16, 12)
        fc_layout.setSpacing(12)

        # Action filter
        action_label = QLabel("Action:")
        action_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #374151; border: none;")
        fc_layout.addWidget(action_label)
        self.action_filter = QComboBox()
        self.action_filter.addItem("All", "all")
        self.action_filter.setMinimumWidth(140)
        self.action_filter.setStyleSheet(self._combo_style())
        self.action_filter.currentIndexChanged.connect(self.apply_filters)
        fc_layout.addWidget(self.action_filter)

        # Search
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #374151; border: none;")
        fc_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("User or document name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px; border: 1px solid #d1d5db; border-radius: 8px;
                font-size: 13px; background: white;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self.search_input.textChanged.connect(self.apply_filters)
        fc_layout.addWidget(self.search_input, stretch=1)

        # Refresh
        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; border: none;
                border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        fc_layout.addWidget(refresh_btn)

        layout.addWidget(filter_card)

        # ── Table Card ──
        table_card = QFrame()
        table_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
        """)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Document", "User", "Action", "Timestamp"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)

        vh = self.table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            vh.setDefaultSectionSize(48)

        hh = self.table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(1, 180)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(2, 160)
            hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(3, 180)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff; border: none;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 0px; border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget::item:selected {
                background-color: #f9fafb; color: #1f2937;
            }
            QHeaderView::section {
                background-color: #f9fafb; color: #6b7280; padding: 12px 8px;
                border: none; border-bottom: 2px solid #e5e7eb;
                font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
            }
        """)
        tc_layout.addWidget(self.table)
        layout.addWidget(table_card)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #9ca3af; font-size: 12px; padding: 2px 0;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Auto-refresh timer
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_data)

    # ── Helpers ──

    @staticmethod
    def _combo_style() -> str:
        return """
            QComboBox {
                padding: 8px 14px; border: 1px solid #d1d5db; border-radius: 8px;
                font-size: 13px; background: white; min-width: 120px;
            }
            QComboBox:focus { border-color: #3b82f6; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: white; border: 1px solid #e5e7eb; border-radius: 6px;
                selection-background-color: #f3f4f6; selection-color: #1f2937;
            }
        """

    # ── Data ──

    def refresh_data(self):
        if not self.api_client.is_admin():
            self.auto_refresh_timer.stop()
            self.status_label.setText("Admin access required")
            return

        try:
            self.status_label.setText("Loading access logs...")
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/security/access-logs",
                params={"limit": 200},
                timeout=10,
            )
            if response.status_code == 200:
                self.logs = response.json()
                self._rebuild_action_filter()
                self.apply_filters()
                self.status_label.setText(
                    f"Loaded {len(self.logs)} logs — {datetime.now().strftime('%H:%M:%S')}")
            elif response.status_code == 401:
                self.auto_refresh_timer.stop()
                self.status_label.setText("Not authenticated")
            else:
                self.status_label.setText(f"Error: {response.status_code}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def _rebuild_action_filter(self):
        """Populate action filter dynamically from log data."""
        current = self.action_filter.currentData()
        self.action_filter.blockSignals(True)
        self.action_filter.clear()
        self.action_filter.addItem("All", "all")

        seen: set[str] = set()
        for log in self.logs:
            norm = _normalise_action(log.get('action', ''))
            if norm and norm not in seen:
                seen.add(norm)
                style = _ACTION_STYLE.get(norm)
                icon = qta.icon(style[0], color=style[1]) if style else qta.icon('fa5s.circle', color='#9ca3af')
                self.action_filter.addItem(icon, norm.replace('_', ' ').title(), norm)

        if current:
            idx = self.action_filter.findData(current)
            if idx >= 0:
                self.action_filter.setCurrentIndex(idx)
        self.action_filter.blockSignals(False)

    def apply_filters(self):
        filtered = self.logs

        raw_action = self.action_filter.currentData()
        if raw_action and raw_action != "all":
            filtered = [l for l in filtered if _normalise_action(l.get('action', '')) == raw_action]

        search = self.search_input.text().lower()
        if search:
            filtered = [
                l for l in filtered
                if search in l.get('document', {}).get('filename', '').lower()
                or search in f"{l.get('user', {}).get('first_name', '')} {l.get('user', {}).get('last_name', '')}".lower()
                or search in l.get('action', '').lower()
            ]

        self.populate_table(filtered)

    def populate_table(self, logs):
        self.table.setRowCount(0)
        for log in logs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 48)

            # Document
            doc = log.get('document', {})
            doc_name = doc.get('filename', 'Unknown') if doc else 'Unknown'
            doc_item = QTableWidgetItem(doc_name)
            doc_item.setForeground(QColor('#1f2937'))
            self.table.setItem(row, 0, doc_item)

            # User
            user = log.get('user', {})
            if user:
                name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                if not name:
                    name = user.get('username', 'Unknown')
            else:
                name = 'Unknown'
            user_item = QTableWidgetItem(name)
            user_item.setForeground(QColor('#6b7280'))
            self.table.setItem(row, 1, user_item)

            # Action badge
            raw = log.get('action', '')
            norm = _normalise_action(raw)
            style = _ACTION_STYLE.get(norm, ("fa5s.circle", "#6b7280", "#f3f4f6"))
            badge = QWidget()
            badge_layout = QHBoxLayout(badge)
            badge_layout.setContentsMargins(8, 4, 8, 4)
            badge_layout.setSpacing(6)

            act_icon = QLabel()
            act_icon.setPixmap(qta.icon(style[0], color=style[1]).pixmap(14, 14))
            act_icon.setStyleSheet("border: none;")
            badge_layout.addWidget(act_icon)

            act_text = QLabel(norm.replace('_', ' ').title())
            act_text.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {style[1]}; border: none;")
            badge_layout.addWidget(act_text)
            badge_layout.addStretch()

            badge.setStyleSheet(f"background-color: {style[2]}; border-radius: 6px;")
            self.table.setCellWidget(row, 2, badge)

            # Timestamp
            ts = log.get('access_time', '')
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                formatted = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                formatted = str(ts) if ts else 'N/A'
            ts_item = QTableWidgetItem(formatted)
            ts_item.setForeground(QColor('#9ca3af'))
            self.table.setItem(row, 3, ts_item)

    def showEvent(self, event):
        super().showEvent(event)
        if self.api_client.is_admin():
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start(30000)
            self.refresh_data()
        else:
            self.status_label.setText("Admin access required")

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
