from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QListWidget, QListWidgetItem, QPushButton
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from api.client import APIClient

class DashboardView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.summary_data = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Welcome & User Context
        welcome_group = QGroupBox("Welcome")
        welcome_layout = QVBoxLayout(welcome_group)
        self.welcome_label = QLabel("Loading...")
        welcome_layout.addWidget(self.welcome_label)
        layout.addWidget(welcome_group)

        # Document Overview
        overview_group = QGroupBox("Document Overview")
        overview_layout = QHBoxLayout(overview_group)
        
        self.total_docs_label = QLabel("Total Documents: --")
        self.my_docs_label = QLabel("My Documents: --")
        self.shared_docs_label = QLabel("Shared With Me: --")
        self.internal_dept_label = QLabel("Internal Dept: --")
        self.public_docs_label = QLabel("Public Documents: --")
        
        overview_layout.addWidget(self.total_docs_label)
        overview_layout.addWidget(self.my_docs_label)
        overview_layout.addWidget(self.shared_docs_label)
        overview_layout.addWidget(self.internal_dept_label)
        overview_layout.addWidget(self.public_docs_label)
        
        layout.addWidget(overview_group)

        # Classification Chart
        chart_group = QGroupBox("Document Classification Breakdown")
        chart_layout = QVBoxLayout(chart_group)
        self.chart_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        chart_layout.addWidget(self.chart_canvas)
        layout.addWidget(chart_group)

        # Security Alerts
        alerts_group = QGroupBox("Recent Security Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        self.alerts_list = QListWidget()
        alerts_layout.addWidget(self.alerts_list)
        layout.addWidget(alerts_group)

        # Recent Activity
        activity_group = QGroupBox("Recent Document Activity")
        activity_layout = QVBoxLayout(activity_group)
        self.activity_list = QListWidget()
        activity_layout.addWidget(self.activity_list)
        layout.addWidget(activity_group)

        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        self.upload_btn = QPushButton("📤 Upload New Document")
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.upload_btn.clicked.connect(self.navigate_to_upload)
        
        self.my_docs_btn = QPushButton("📁 View My Documents")
        self.my_docs_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.my_docs_btn.clicked.connect(self.navigate_to_my_docs)
        
        self.logs_btn = QPushButton("🔒 View Security Logs")
        self.logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.logs_btn.clicked.connect(self.navigate_to_logs)
        
        actions_layout.addWidget(self.upload_btn)
        actions_layout.addWidget(self.my_docs_btn)
        actions_layout.addWidget(self.logs_btn)
        
        layout.addWidget(actions_group)

    def refresh_data(self):
        self.summary_data = self.api_client.get_dashboard_summary()
        if self.summary_data:
            self.update_ui()

    def update_ui(self):
        data = self.summary_data
        if not data:
            return
        
        # Welcome
        user = self.api_client.get_current_user()
        if user:
            self.welcome_label.setText(f"Welcome, {user['username']}!")

        # Overview
        self.total_docs_label.setText(f"Total Documents: {data['total_documents']}")
        self.my_docs_label.setText(f"My Documents: {data['owned_documents']}")
        self.shared_docs_label.setText(f"Shared With Me: {data['shared_documents']}")
        self.internal_dept_label.setText(f"Internal Dept: {data['internal_department_documents']}")
        # Public docs would need separate query, for now approximate
        self.public_docs_label.setText(f"Public Documents: {data['classification_summary'].get('public', 0)}")

        # Chart
        self.update_chart(data['classification_summary'])

        # Security Alerts
        self.alerts_list.clear()
        for log in data['recent_security_logs'][:5]:
            item_text = f"{log['timestamp'][:19]} - {log['activity_type']}"
            if log.get('user') and log['user'].get('username'):
                item_text += f" ({log['user']['username']})"
            self.alerts_list.addItem(item_text)

        # Recent Activity
        self.activity_list.clear()
        for log in data['recent_access_logs'][:5]:
            item_text = f"{log['timestamp'][:19]} - {log['action']} - {log['document']['filename']}"
            if log.get('user') and log['user'].get('username'):
                item_text += f" by {log['user']['username']}"
            self.activity_list.addItem(item_text)

    def update_chart(self, classification_data):
        self.chart_canvas.figure.clear()
        ax = self.chart_canvas.figure.add_subplot(111)
        
        labels = list(classification_data.keys())
        sizes = list(classification_data.values())
        
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        
        self.chart_canvas.draw()
    
    def navigate_to_upload(self):
        """Navigate to upload document view."""
        main_window = self.window()
        if hasattr(main_window, 'content_stack'):
            main_window.content_stack.setCurrentIndex(5)
    
    def navigate_to_my_docs(self):
        """Navigate to my documents view."""
        main_window = self.window()
        if hasattr(main_window, 'content_stack'):
            main_window.content_stack.setCurrentIndex(1)
            if hasattr(main_window, 'my_documents_view'):
                main_window.my_documents_view.refresh_data()
    
    def navigate_to_logs(self):
        """Navigate to security logs view (admin only)."""
        from PyQt6.QtWidgets import QMessageBox
        if self.api_client.is_admin():
            main_window = self.window()
            if hasattr(main_window, 'content_stack'):
                main_window.content_stack.setCurrentIndex(7)
                if hasattr(main_window, 'security_logs_view'):
                    main_window.security_logs_view.refresh_data()
        else:
            QMessageBox.warning(self, "Access Denied", "Only administrators can view security logs.")