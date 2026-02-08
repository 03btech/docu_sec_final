from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QGroupBox, QListWidget, QListWidgetItem,
                              QPushButton, QGridLayout,
                              QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon
import qtawesome as qta
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from api.client import APIClient
from datetime import datetime, timezone


class DashboardLoadWorker(QThread):
    """Load dashboard data off the main thread."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_client: APIClient):
        super().__init__()
        self._api = api_client

    def run(self):
        try:
            data = self._api.get_dashboard_summary()
            self.finished.emit(data if data else {})
        except Exception as e:
            self.error.emit(str(e))


def _stat_card(icon_name: str, icon_color: str, bg_color: str, 
               value_text: str, label_text: str) -> QWidget:
    """Create a modern stat card widget."""
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0px;
        }}
    """)
    card.setFixedHeight(110)

    layout = QHBoxLayout(card)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(14)

    # Icon circle
    icon_label = QLabel()
    icon_label.setFixedSize(48, 48)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setStyleSheet(f"""
        QLabel {{
            background-color: {bg_color};
            border-radius: 24px;
            border: none;
        }}
    """)
    icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(24, 24))
    layout.addWidget(icon_label)

    # Text
    text_layout = QVBoxLayout()
    text_layout.setSpacing(2)

    value = QLabel(value_text)
    value.setStyleSheet("QLabel { font-size: 26px; font-weight: bold; color: #1f2937; border: none; }")
    value.setObjectName("stat_value")
    text_layout.addWidget(value)

    label = QLabel(label_text)
    label.setStyleSheet("QLabel { font-size: 12px; color: #6b7280; border: none; }")
    text_layout.addWidget(label)

    layout.addLayout(text_layout)
    layout.addStretch()
    return card


class DashboardView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.summary_data = None
        self._load_worker = None
        self.setup_ui()

    def setup_ui(self):
        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Dashboard")
        title.setStyleSheet("QLabel { font-size: 28px; font-weight: bold; color: #1f2937; }")
        layout.addWidget(title)

        self.welcome_label = QLabel("Welcome back!")
        self.welcome_label.setStyleSheet("QLabel { font-size: 14px; color: #6b7280; margin-bottom: 4px; }")
        layout.addWidget(self.welcome_label)

        # Loading state
        self.loading_label = QLabel("Loading dashboard data...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("QLabel { color: #6b7280; font-size: 14px; padding: 40px; }")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # ── Stat Cards Row ──
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)

        self.card_total = _stat_card('fa5s.file-alt', '#3b82f6', '#dbeafe', '--', 'Total Documents')
        self.card_my = _stat_card('fa5s.user', '#27ae60', '#d1fae5', '--', 'My Documents')
        self.card_shared = _stat_card('fa5s.share-alt', '#8b5cf6', '#ede9fe', '--', 'Shared With Me')
        self.card_dept = _stat_card('fa5s.building', '#f59e0b', '#fef3c7', '--', 'Dept Documents')

        self.stats_grid.addWidget(self.card_total, 0, 0)
        self.stats_grid.addWidget(self.card_my, 0, 1)
        self.stats_grid.addWidget(self.card_shared, 0, 2)
        self.stats_grid.addWidget(self.card_dept, 0, 3)
        layout.addLayout(self.stats_grid)

        # ── Middle row: Chart + Security Alerts side by side ──
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Classification Chart
        chart_card = QFrame()
        chart_card.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
        """)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        chart_title = QLabel("Classification Breakdown")
        chart_title.setStyleSheet("QLabel { font-size: 16px; font-weight: 600; color: #1f2937; border: none; }")
        chart_layout.addWidget(chart_title)
        self.chart_canvas = FigureCanvas(Figure(figsize=(4, 3)))
        self.chart_canvas.figure.set_facecolor('#ffffff')
        chart_layout.addWidget(self.chart_canvas)
        mid_row.addWidget(chart_card, stretch=1)

        # Security Alerts
        alerts_card = QFrame()
        alerts_card.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
        """)
        alerts_layout = QVBoxLayout(alerts_card)
        alerts_layout.setContentsMargins(16, 16, 16, 16)
        alerts_header = QHBoxLayout()
        alerts_title = QLabel("Recent Security Alerts")
        alerts_title.setStyleSheet("QLabel { font-size: 16px; font-weight: 600; color: #1f2937; border: none; }")
        alerts_header.addWidget(alerts_title)
        alerts_header.addStretch()
        self.alerts_count_badge = QLabel("")
        self.alerts_count_badge.setStyleSheet("""
            QLabel { background-color: #fef2f2; color: #ef4444; border: none;
                     border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
        """)
        self.alerts_count_badge.setVisible(False)
        alerts_header.addWidget(self.alerts_count_badge)
        alerts_layout.addLayout(alerts_header)
        self.alerts_list = QListWidget()
        self.alerts_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; font-size: 13px; color: #374151; }
            QListWidget::item { padding: 10px 6px; border-bottom: 1px solid #f3f4f6; }
            QListWidget::item:hover { background-color: #f9fafb; }
        """)
        self.alerts_list.setIconSize(QSize(20, 20))
        alerts_layout.addWidget(self.alerts_list)
        self.alerts_empty = QLabel("No security alerts")
        self.alerts_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alerts_empty.setStyleSheet("QLabel { color: #9ca3af; font-size: 13px; padding: 30px; border: none; }")
        self.alerts_empty.setVisible(False)
        alerts_layout.addWidget(self.alerts_empty)
        mid_row.addWidget(alerts_card, stretch=1)

        layout.addLayout(mid_row)

        # ── Recent Activity ──
        activity_card = QFrame()
        activity_card.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
        """)
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 16, 16, 16)
        activity_title = QLabel("Recent Document Activity")
        activity_title.setStyleSheet("QLabel { font-size: 16px; font-weight: 600; color: #1f2937; border: none; }")
        activity_layout.addWidget(activity_title)
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; font-size: 13px; color: #374151; }
            QListWidget::item { padding: 10px 6px; border-bottom: 1px solid #f3f4f6; }
            QListWidget::item:hover { background-color: #f9fafb; }
        """)
        self.activity_list.setIconSize(QSize(18, 18))
        self.activity_list.setMaximumHeight(220)
        activity_layout.addWidget(self.activity_list)
        self.activity_empty = QLabel("No recent activity")
        self.activity_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity_empty.setStyleSheet("QLabel { color: #9ca3af; font-size: 13px; padding: 30px; border: none; }")
        self.activity_empty.setVisible(False)
        activity_layout.addWidget(self.activity_empty)
        layout.addWidget(activity_card)

        # ── Quick Actions ──
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.upload_btn = QPushButton("  Upload Document")
        self.upload_btn.setIcon(qta.icon('fa5s.cloud-upload-alt', color='white'))
        self.upload_btn.setStyleSheet(self._quick_btn_style('#27ae60', '#229954'))
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.clicked.connect(self.navigate_to_upload)
        actions_row.addWidget(self.upload_btn)

        self.my_docs_btn = QPushButton("  My Documents")
        self.my_docs_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.my_docs_btn.setStyleSheet(self._quick_btn_style('#3b82f6', '#2563eb'))
        self.my_docs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.my_docs_btn.clicked.connect(self.navigate_to_my_docs)
        actions_row.addWidget(self.my_docs_btn)

        self.logs_btn = QPushButton("  Security Logs")
        self.logs_btn.setIcon(qta.icon('fa5s.shield-alt', color='white'))
        self.logs_btn.setStyleSheet(self._quick_btn_style('#ef4444', '#dc2626'))
        self.logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logs_btn.clicked.connect(self.navigate_to_logs)
        actions_row.addWidget(self.logs_btn)

        actions_row.addStretch()
        layout.addLayout(actions_row)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @staticmethod
    def _quick_btn_style(bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """

    # ── Data Loading ──

    def refresh_data(self):
        self.loading_label.setVisible(True)
        self._load_worker = DashboardLoadWorker(self.api_client)
        self._load_worker.finished.connect(self._on_data_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_data_loaded(self, data):
        self.loading_label.setVisible(False)
        self.summary_data = data
        if data:
            self.update_ui()

    def _on_load_error(self, msg):
        self.loading_label.setVisible(False)

    # ── UI Updates ──

    def _set_card_value(self, card: QWidget, value: str):
        lbl = card.findChild(QLabel, "stat_value")
        if lbl:
            lbl.setText(str(value))

    def update_ui(self):
        data = self.summary_data
        if not data:
            return

        user = self.api_client.get_current_user()
        if user:
            name = user.get('first_name') or user.get('username', 'User')
            self.welcome_label.setText(f"Welcome back, {name}!")

        self._set_card_value(self.card_total, str(data.get('total_documents', 0)))
        self._set_card_value(self.card_my, str(data.get('owned_documents', 0)))
        self._set_card_value(self.card_shared, str(data.get('shared_documents', 0)))
        self._set_card_value(self.card_dept, str(data.get('internal_department_documents', 0)))

        # Chart
        self.update_chart(data.get('classification_summary', {}))

        # Security Alerts
        security_logs = data.get('recent_security_logs', [])
        self.alerts_list.clear()
        if security_logs:
            self.alerts_empty.setVisible(False)
            self.alerts_list.setVisible(True)
            self.alerts_count_badge.setText(str(len(security_logs)))
            self.alerts_count_badge.setVisible(True)
            for log in security_logs[:8]:
                item = self._make_security_item(log)
                self.alerts_list.addItem(item)
        else:
            self.alerts_list.setVisible(False)
            self.alerts_empty.setVisible(True)
            self.alerts_count_badge.setVisible(False)

        # Recent Activity
        access_logs = data.get('recent_access_logs', [])
        self.activity_list.clear()
        if access_logs:
            self.activity_empty.setVisible(False)
            self.activity_list.setVisible(True)
            for log in access_logs[:8]:
                item = self._make_activity_item(log)
                self.activity_list.addItem(item)
        else:
            self.activity_list.setVisible(False)
            self.activity_empty.setVisible(True)

    # ── List Item Builders ──

    _SECURITY_ICONS = {
        'phone_detected': ('fa5s.mobile-alt', '#ef4444'),
        'no_person_detected': ('fa5s.user-slash', '#f59e0b'),
        'low_lighting_detected': ('fa5s.lightbulb', '#f59e0b'),
        'viewer_closed_low_lighting': ('fa5s.times-circle', '#f59e0b'),
        'viewer_closed_phone_detection': ('fa5s.times-circle', '#ef4444'),
        'screen_capture_protection_enabled': ('fa5s.desktop', '#3b82f6'),
        'screenshot_attempt': ('fa5s.camera', '#ef4444'),
    }

    def _make_security_item(self, log: dict) -> QListWidgetItem:
        activity = log.get('activity_type', 'unknown')
        ts = self._format_relative_time(log.get('timestamp', ''))
        user_name = ''
        if log.get('user') and log['user'].get('username'):
            user_name = log['user']['username']

        label = activity.replace('_', ' ').title()
        text = f"{label}"
        if user_name:
            text += f"  —  {user_name}"
        text += f"\n{ts}"

        icon_name, icon_color = self._SECURITY_ICONS.get(activity, ('fa5s.exclamation-triangle', '#9ca3af'))
        item = QListWidgetItem(qta.icon(icon_name, color=icon_color), text)
        item.setSizeHint(QSize(0, 48))
        return item

    _ACTION_ICONS = {
        'view': ('fa5s.eye', '#3b82f6'),
        'download': ('fa5s.download', '#27ae60'),
        'upload': ('fa5s.cloud-upload-alt', '#8b5cf6'),
        'delete': ('fa5s.trash', '#ef4444'),
        'share': ('fa5s.share-alt', '#f59e0b'),
    }

    def _make_activity_item(self, log: dict) -> QListWidgetItem:
        action = log.get('action', 'unknown')
        filename = log.get('document', {}).get('filename', '') if log.get('document') else ''
        ts = self._format_relative_time(log.get('timestamp', ''))
        user_name = ''
        if log.get('user') and log['user'].get('username'):
            user_name = log['user']['username']

        text = f"{action.title()}"
        if filename:
            text += f"  —  {filename}"
        if user_name:
            text += f"  by {user_name}"
        text += f"\n{ts}"

        icon_name, icon_color = self._ACTION_ICONS.get(action.lower(), ('fa5s.file', '#6b7280'))
        item = QListWidgetItem(qta.icon(icon_name, color=icon_color), text)
        item.setSizeHint(QSize(0, 48))
        return item

    @staticmethod
    def _format_relative_time(iso_ts: str) -> str:
        """Convert ISO timestamp to a human-friendly relative string."""
        if not iso_ts:
            return ''
        try:
            dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - dt
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return 'Just now'
            elif seconds < 3600:
                m = seconds // 60
                return f'{m}m ago'
            elif seconds < 86400:
                h = seconds // 3600
                return f'{h}h ago'
            elif seconds < 604800:
                d = seconds // 86400
                return f'{d}d ago'
            else:
                return dt.strftime('%b %d, %Y')
        except Exception:
            return iso_ts[:19]

    def update_chart(self, classification_data):
        self.chart_canvas.figure.clear()
        ax = self.chart_canvas.figure.add_subplot(111)

        labels = list(classification_data.keys())
        sizes = list(classification_data.values())

        colors = {
            'public': '#3b82f6',
            'internal': '#f59e0b',
            'confidential': '#ef4444',
        }
        pie_colors = [colors.get(l.lower(), '#9ca3af') for l in labels]

        if sizes and any(s > 0 for s in sizes):
            ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90,
                   colors=pie_colors, textprops={'fontsize': 11})
            ax.axis('equal')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                    fontsize=14, color='#9ca3af')
            ax.set_axis_off()

        self.chart_canvas.figure.tight_layout()
        self.chart_canvas.draw()

    # ── Quick-Action Navigation (uses MainWindow._switch_to) ──

    def navigate_to_upload(self):
        main_window = self.window()
        if hasattr(main_window, '_switch_to'):
            main_window._switch_to("Upload Document")

    def navigate_to_my_docs(self):
        main_window = self.window()
        if hasattr(main_window, '_switch_to'):
            main_window._switch_to("My Documents")

    def navigate_to_logs(self):
        main_window = self.window()
        if hasattr(main_window, '_switch_to'):
            main_window._switch_to("Security Logs")