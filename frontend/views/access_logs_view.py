"""
Access Logs View - Display document access logs
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView,
                             QMessageBox, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import APIClient
from datetime import datetime


class AccessLogsView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.logs = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Access Logs")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Description
        description = QLabel("View all document access activities in the system")
        description.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 20px;")
        layout.addWidget(description)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Action filter
        filter_layout.addWidget(QLabel("Action:"))
        self.action_filter = QComboBox()
        self.action_filter.addItems(["All", "View", "Download", "Edit", "Delete"])
        self.action_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.action_filter)
        
        # Search filter
        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by user or document...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        filter_layout.addWidget(refresh_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Document", "User", "Action", "Timestamp"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Auto-refresh timer (every 30 seconds) - only start if user is admin
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        # Timer will be started in showEvent if user is admin

    def refresh_data(self):
        """Fetch access logs from the API"""
        # Check if user is admin before attempting to fetch logs
        if not self.api_client.is_admin():
            print("⚠️ Access Logs: User is not admin, skipping refresh")
            self.auto_refresh_timer.stop()
            self.status_label.setText("Admin access required")
            return
        
        try:
            self.status_label.setText("Loading access logs...")
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/security/access-logs",
                params={"limit": 100},
                timeout=10  # Add timeout
            )
            
            if response.status_code == 200:
                new_logs = response.json()
                print(f"✅ Access Logs: Received {len(new_logs)} logs from backend")
                
                # Store the original logs
                self.logs = new_logs
                
                # Apply current filters to display
                self.apply_filters()
            elif response.status_code == 401:
                # User is not authenticated - stop timer to prevent repeated errors
                print("⚠️ Access Logs: Not authenticated, stopping auto-refresh")
                self.auto_refresh_timer.stop()
                self.status_label.setText("Not authenticated")
                return
                
                self.status_label.setText(f"Loaded {len(self.logs)} access logs (Last updated: {datetime.now().strftime('%H:%M:%S')})")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"❌ Access Logs Error: {error_msg}")
                self.status_label.setText(f"Error: {response.status_code}")
                QMessageBox.warning(self, "Error", f"Failed to load access logs: {error_msg}")
        except Exception as e:
            print(f"❌ Access Logs Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load access logs: {str(e)}")

    def apply_filters(self):
        """Apply filters to the logs"""
        filtered_logs = self.logs
        
        # Filter by action
        action_filter = self.action_filter.currentText()
        if action_filter != "All":
            filtered_logs = [log for log in filtered_logs if log.get('action', '').lower() == action_filter.lower()]
        
        # Filter by search text
        search_text = self.search_input.text().lower()
        if search_text:
            filtered_logs = [
                log for log in filtered_logs
                if search_text in log.get('document', {}).get('filename', '').lower() or
                   search_text in f"{log.get('user', {}).get('first_name', '')} {log.get('user', {}).get('last_name', '')}".lower()
            ]
        
        self.populate_table(filtered_logs)

    def populate_table(self, logs):
        """Populate the table with logs"""
        self.table.setRowCount(0)
        
        for log in logs:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Document name
            document = log.get('document', {})
            document_name = document.get('filename', 'Unknown Document') if document else 'Unknown Document'
            self.table.setItem(row_position, 0, QTableWidgetItem(document_name))
            
            # User full name
            user = log.get('user', {})
            if user:
                user_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                if not user_full_name:
                    user_full_name = user.get('username', 'Unknown User')
            else:
                user_full_name = 'Unknown User'
            self.table.setItem(row_position, 1, QTableWidgetItem(user_full_name))
            
            # Action
            action_item = QTableWidgetItem(log.get('action', 'N/A'))
            # Color code actions
            action = log.get('action', '').lower()
            if action == 'view':
                action_item.setBackground(QColor('#d5f4e6'))
            elif action == 'download':
                action_item.setBackground(QColor('#d1ecf1'))
            elif action == 'edit':
                action_item.setBackground(QColor('#fff3cd'))
            elif action == 'delete':
                action_item.setBackground(QColor('#f8d7da'))
            self.table.setItem(row_position, 2, action_item)
            
            # Timestamp (convert from UTC to local timezone)
            timestamp = log.get('access_time', '')
            try:
                # Parse ISO format timestamp with timezone
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Convert to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = str(timestamp) if timestamp else 'N/A'
            self.table.setItem(row_position, 3, QTableWidgetItem(formatted_time))

    def showEvent(self, event):
        """Refresh data when view is shown"""
        super().showEvent(event)
        # Only refresh and start timer if user is admin
        if self.api_client.is_admin():
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start(30000)  # 30 seconds
            self.refresh_data()
        else:
            self.status_label.setText("Admin access required")
    
    def hideEvent(self, event):
        """Stop timer when view is hidden"""
        super().hideEvent(event)
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
            print("ℹ️ Access Logs: Timer stopped (view hidden)")
