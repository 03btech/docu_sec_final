"""
Security Logs View — Modern card-based layout with dynamic filters and event badges.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView,
                             QMessageBox, QComboBox, QLineEdit, QFrame, QScrollArea,
                             QTextEdit, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor
import qtawesome as qta
from api.client import APIClient
from datetime import datetime
import json
import csv

# ── Activity type display mapping ──
_ACTIVITY_STYLE: dict[str, tuple[str, str, str, str]] = {
    # activity_type → (icon, text_color, bg_color, display_label)
    "phone_detected":                   ("fa5s.mobile-alt",     "#dc2626", "#fee2e2", "Phone Detected"),
    "no_person_detected":               ("fa5s.user-slash",     "#d97706", "#fef3c7", "No Person"),
    "low_lighting_detected":            ("fa5s.adjust",         "#92400e", "#fef3c7", "Low Lighting"),
    "viewer_closed_low_lighting":       ("fa5s.door-open",      "#9f1239", "#ffe4e6", "Closed — Low Light"),
    "viewer_closed_phone_detection":    ("fa5s.door-open",      "#dc2626", "#fee2e2", "Closed — Phone"),
    "screen_capture_protection_enabled":("fa5s.shield-alt",     "#16a34a", "#dcfce7", "Screen Protection"),
    "ai_detection_verified":            ("fa5s.check-circle",   "#059669", "#d1fae5", "AI Verified"),
    "screenshot_attempt":               ("fa5s.camera",         "#dc2626", "#fee2e2", "Screenshot Attempt"),
}

def _display_label(activity_type: str) -> str:
    style = _ACTIVITY_STYLE.get(activity_type)
    if style:
        return style[3]
    return activity_type.replace('_', ' ').title()


class SecurityLogsView(QWidget):

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.logs: list[dict] = []
        self.filtered_logs: list[dict] = []
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
        title = QLabel("Security Logs")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)

        desc = QLabel("Monitor security events: phone detection, person absence, and lighting alerts")
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

        # Event type filter
        type_label = QLabel("Event:")
        type_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #374151; border: none;")
        fc_layout.addWidget(type_label)
        self.activity_filter = QComboBox()
        self.activity_filter.addItem("All", "all")
        self.activity_filter.setMinimumWidth(180)
        self.activity_filter.setStyleSheet(self._combo_style())
        self.activity_filter.currentIndexChanged.connect(self.apply_filters)
        fc_layout.addWidget(self.activity_filter)

        # Search
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #374151; border: none;")
        fc_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("User name...")
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

        # Download CSV
        download_btn = QPushButton("  Download CSV")
        download_btn.setIcon(qta.icon('fa5s.file-csv', color='white'))
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a; color: white; border: none;
                border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #15803d; }
        """)
        download_btn.clicked.connect(self._download_csv)
        fc_layout.addWidget(download_btn)

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
        self.table.setHorizontalHeaderLabels(["User", "Event", "Details", "Timestamp"])
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
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(0, 180)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(1, 190)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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
        self.table.currentCellChanged.connect(self._on_row_changed)
        tc_layout.addWidget(self.table)
        layout.addWidget(table_card)

        # ── Details Card (expandable) ──
        self.details_card = QFrame()
        self.details_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
        """)
        dc_layout = QVBoxLayout(self.details_card)
        dc_layout.setContentsMargins(16, 12, 16, 12)
        dc_layout.setSpacing(8)

        dc_header = QHBoxLayout()
        detail_icon = QLabel()
        detail_icon.setPixmap(qta.icon('fa5s.info-circle', color='#3b82f6').pixmap(16, 16))
        detail_icon.setStyleSheet("border: none;")
        dc_header.addWidget(detail_icon)
        dc_title = QLabel("Event Details")
        dc_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1f2937; border: none;")
        dc_header.addWidget(dc_title)
        dc_header.addStretch()
        
        # Close details button
        close_details_btn = QPushButton()
        close_details_btn.setIcon(qta.icon('fa5s.times', color='#6b7280'))
        close_details_btn.setFixedSize(28, 28)
        close_details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_details_btn.setToolTip("Close details")
        close_details_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6; border: none; border-radius: 14px;
            }
            QPushButton:hover { background-color: #fee2e2; }
        """)
        close_details_btn.clicked.connect(self._close_details)
        dc_header.addWidget(close_details_btn)
        
        dc_layout.addLayout(dc_header)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFixedHeight(120)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
                padding: 10px; font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px; color: #374151;
            }
        """)
        dc_layout.addWidget(self.details_text)

        self.details_card.setVisible(False)
        layout.addWidget(self.details_card)

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

    # ── Download ──

    def _download_csv(self):
        """Export currently displayed table rows to a CSV file."""
        row_count = self.table.rowCount()
        if row_count == 0:
            QMessageBox.information(self, "No Data", "There are no logs to download.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Security Logs", "security_logs.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["User", "Event", "Details", "Timestamp"])
                for row in range(row_count):
                    user_item = self.table.item(row, 0)
                    # Event is a cell widget (badge), extract text
                    event_widget = self.table.cellWidget(row, 1)
                    event_text = ""
                    if event_widget:
                        labels = event_widget.findChildren(QLabel)
                        for lbl in labels:
                            if lbl.text() and not lbl.pixmap():
                                event_text = lbl.text()
                                break
                    detail_item = self.table.item(row, 2)
                    ts_item = self.table.item(row, 3)
                    writer.writerow([
                        user_item.text() if user_item else "",
                        event_text,
                        detail_item.text() if detail_item else "",
                        ts_item.text() if ts_item else "",
                    ])
            self.status_label.setText(f"✅ Exported {row_count} logs to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to save CSV: {e}")

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
            self.status_label.setText("Loading security logs...")
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/security/logs",
                params={"limit": 200},
                timeout=10,
            )
            if response.status_code == 200:
                self.logs = response.json()
                self._rebuild_activity_filter()
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

    def _rebuild_activity_filter(self):
        """Populate activity filter dynamically from log data."""
        current = self.activity_filter.currentData()
        self.activity_filter.blockSignals(True)
        self.activity_filter.clear()
        self.activity_filter.addItem("All", "all")

        seen: set[str] = set()
        for log in self.logs:
            at = log.get('activity_type', '')
            if at and at not in seen:
                seen.add(at)
                style = _ACTIVITY_STYLE.get(at)
                icon = qta.icon(style[0], color=style[1]) if style else qta.icon('fa5s.circle', color='#9ca3af')
                self.activity_filter.addItem(icon, _display_label(at), at)

        if current:
            idx = self.activity_filter.findData(current)
            if idx >= 0:
                self.activity_filter.setCurrentIndex(idx)
        self.activity_filter.blockSignals(False)

    def apply_filters(self):
        filtered = self.logs

        raw_type = self.activity_filter.currentData()
        if raw_type and raw_type != "all":
            filtered = [l for l in filtered if l.get('activity_type', '') == raw_type]

        search = self.search_input.text().lower()
        if search:
            filtered = [
                l for l in filtered
                if search in self._user_name(l).lower()
                or search in _display_label(l.get('activity_type', '')).lower()
            ]

        self.filtered_logs = filtered
        self.populate_table(filtered)

    @staticmethod
    def _user_name(log: dict) -> str:
        user = log.get('user')
        if not user:
            return 'Unknown'
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        return name if name else user.get('username', 'Unknown')

    def populate_table(self, logs):
        self.table.setRowCount(0)
        self.details_card.setVisible(False)

        for log in logs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 48)

            # User
            name = self._user_name(log)
            user_item = QTableWidgetItem(name)
            user_item.setForeground(QColor('#1f2937'))
            self.table.setItem(row, 0, user_item)

            # Activity badge
            at = log.get('activity_type', '')
            style = _ACTIVITY_STYLE.get(at, ("fa5s.circle", "#6b7280", "#f3f4f6", at.replace('_', ' ').title()))
            badge = QWidget()
            badge_layout = QHBoxLayout(badge)
            badge_layout.setContentsMargins(8, 4, 8, 4)
            badge_layout.setSpacing(6)

            act_icon = QLabel()
            act_icon.setPixmap(qta.icon(style[0], color=style[1]).pixmap(14, 14))
            act_icon.setStyleSheet("border: none;")
            badge_layout.addWidget(act_icon)

            act_text = QLabel(style[3] if len(style) > 3 else _display_label(at))
            act_text.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {style[1]}; border: none;")
            badge_layout.addWidget(act_text)
            badge_layout.addStretch()

            badge.setStyleSheet(f"background-color: {style[2]}; border-radius: 6px;")
            self.table.setCellWidget(row, 1, badge)

            # Details summary
            details = log.get('details') or {}
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            summary = self._details_summary(details, at)
            detail_item = QTableWidgetItem(summary)
            detail_item.setForeground(QColor('#6b7280'))
            self.table.setItem(row, 2, detail_item)

            # Timestamp
            ts = log.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                formatted = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                formatted = str(ts) if ts else 'N/A'
            ts_item = QTableWidgetItem(formatted)
            ts_item.setForeground(QColor('#9ca3af'))
            self.table.setItem(row, 3, ts_item)

    @staticmethod
    def _details_summary(details: dict, activity_type: str) -> str:
        """Return a short human-readable summary of the details dict."""
        if not details:
            return "—"
        parts: list[str] = []
        if 'document_name' in details:
            parts.append(f"Doc: {details['document_name']}")
        if 'confidence' in details:
            parts.append(f"Conf: {details['confidence']:.0%}" if isinstance(details['confidence'], (int, float)) else f"Conf: {details['confidence']}")
        if 'duration_seconds' in details:
            parts.append(f"Duration: {details['duration_seconds']}s")
        if not parts:
            # Fallback: show first few keys
            for k, v in list(details.items())[:2]:
                parts.append(f"{k.replace('_', ' ').title()}: {v}")
        return " · ".join(parts) if parts else "—"

    def _on_row_changed(self, current_row, _col, _prev_row, _prev_col):
        """Show details card when a row is selected."""
        if current_row < 0 or current_row >= len(self.filtered_logs):
            self.details_card.setVisible(False)
            return

        log = self.filtered_logs[current_row]
        details = log.get('details') or {}
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        if details:
            pretty = json.dumps(details, indent=2, default=str)
            self.details_text.setPlainText(pretty)
            self.details_card.setVisible(True)
        else:
            self.details_card.setVisible(False)
    
    def _close_details(self):
        """Hide the details card and clear selection."""
        self.details_card.setVisible(False)
        self.table.clearSelection()

    # ── Lifecycle ──

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
