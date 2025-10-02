"""
Security Logs View - Display security event logs
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView,
                             QMessageBox, QComboBox, QLineEdit, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import APIClient
from datetime import datetime
import json


class SecurityLogsView(QWidget):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.logs = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Security Logs")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Description
        description = QLabel("View security events and threat detections")
        description.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 20px;")
        layout.addWidget(description)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Activity type filter
        filter_layout.addWidget(QLabel("Activity Type:"))
        self.activity_filter = QComboBox()
        self.activity_filter.addItems(["All", "Phone Detected", "Screenshot Attempt", "No Person Detected"])
        self.activity_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.activity_filter)
        
        # Search filter
        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by user or activity...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        filter_layout.addWidget(refresh_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "User", "Activity Type", "Timestamp", "Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.show_log_details)
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
                background-color: #c0392b;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)
        
        # Details panel
        details_label = QLabel("Log Details:")
        details_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
            }
        """)
        layout.addWidget(self.details_text)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Auto-refresh timer (every 30 seconds) - only start if user is admin
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        # Timer will be started in showEvent if user is admin

    def refresh_data(self):
        """Fetch security logs from the API"""
        # Check if user is admin before attempting to fetch logs
        if not self.api_client.is_admin():
            print("⚠️ Security Logs: User is not admin, skipping refresh")
            self.auto_refresh_timer.stop()
            self.status_label.setText("Admin access required")
            return
        
        try:
            self.status_label.setText("Loading security logs...")
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/security/logs",
                params={"limit": 100},
                timeout=10  # Add timeout
            )
            
            if response.status_code == 200:
                new_logs = response.json()
                print(f"✅ Security Logs: Received {len(new_logs)} logs from backend")
                
                # Store the original logs
                self.logs = new_logs
                
                # Apply current filters to display
                self.apply_filters()
                
                self.status_label.setText(f"Loaded {len(self.logs)} security logs (Last updated: {datetime.now().strftime('%H:%M:%S')})")
            elif response.status_code == 401:
                # User is not authenticated - stop timer to prevent repeated errors
                print("⚠️ Security Logs: Not authenticated, stopping auto-refresh")
                self.auto_refresh_timer.stop()
                self.status_label.setText("Not authenticated")
                return
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"❌ Security Logs Error: {error_msg}")
                self.status_label.setText(f"Error: {response.status_code}")
                QMessageBox.warning(self, "Error", f"Failed to load security logs: {error_msg}")
        except Exception as e:
            print(f"❌ Security Logs Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load security logs: {str(e)}")

    def apply_filters(self):
        """Apply filters to the logs"""
        filtered_logs = self.logs
        
        # Filter by activity type
        activity_filter = self.activity_filter.currentText()
        if activity_filter != "All":
            filtered_logs = [log for log in filtered_logs if activity_filter.lower() in log.get('activity_type', '').lower()]
        
        # Filter by search text
        search_text = self.search_input.text().lower()
        if search_text:
            filtered_logs = [
                log for log in filtered_logs
                if search_text in f"{log.get('user', {}).get('first_name', '')} {log.get('user', {}).get('last_name', '')}".lower() or
                   search_text in log.get('activity_type', '').lower()
            ]
        
        self.populate_table(filtered_logs)

    def populate_table(self, logs):
        """Populate the table with logs"""
        self.table.setRowCount(0)
        
        for log in logs:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # User full name
            user = log.get('user', {})
            if user:
                user_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                if not user_full_name:
                    user_full_name = user.get('username', 'System')
            else:
                user_full_name = 'System'
            self.table.setItem(row_position, 0, QTableWidgetItem(user_full_name))
            
            # Activity Type
            activity_item = QTableWidgetItem(log.get('activity_type', 'N/A'))
            # Color code by severity
            activity_type = log.get('activity_type', '').lower()
            if 'phone' in activity_type or 'no person' in activity_type:
                activity_item.setBackground(QColor('#f8d7da'))  # Red for critical
            elif 'screenshot' in activity_type:
                activity_item.setBackground(QColor('#fff3cd'))  # Yellow for warning
            else:
                activity_item.setBackground(QColor('#d1ecf1'))  # Blue for info
            self.table.setItem(row_position, 1, activity_item)
            
            # Timestamp (convert from UTC to local timezone)
            timestamp = log.get('timestamp', '')
            try:
                # Parse ISO format timestamp with timezone
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Convert to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = str(timestamp) if timestamp else 'N/A'
            self.table.setItem(row_position, 2, QTableWidgetItem(formatted_time))
            
            # Details preview
            details = log.get('details', {})
            if details:
                details_preview = str(details)[:50] + "..." if len(str(details)) > 50 else str(details)
            else:
                details_preview = "No details"
            self.table.setItem(row_position, 3, QTableWidgetItem(details_preview))

    def show_log_details(self):
        """Show full details of selected log"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            self.details_text.clear()
            return
        
        row = selected_items[0].row()
        
        # Find the log by matching the row data
        if row < len(self.logs):
            # Get the current filtered/sorted logs
            # For simplicity, we'll search through all logs
            user_name = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            timestamp_str = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            
            # Find matching log
            log = None
            for l in self.logs:
                user = l.get('user', {})
                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                if not full_name:
                    full_name = user.get('username', 'System')
                if full_name == user_name:
                    log = l
                    break
            
            if not log and self.logs:
                # Fallback to first matching timestamp
                for l in self.logs:
                    try:
                        ts = l.get('timestamp', '')
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        if dt.strftime('%Y-%m-%d %H:%M:%S') == timestamp_str:
                            log = l
                            break
                    except:
                        pass
            
            if log:
                user = log.get('user', {})
                details = {
                    "User": f"{user.get('first_name', '')} {user.get('last_name', '')}" if user else "System",
                    "Username": user.get('username', 'N/A') if user else "N/A",
                    "Activity Type": log.get('activity_type'),
                    "Timestamp": log.get('timestamp'),
                    "Metadata": log.get('details', {})
                }
                self.details_text.setText(json.dumps(details, indent=2))
            else:
                self.details_text.setText("Log details not found")
        else:
            self.details_text.setText("Log details not found")

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
            print("ℹ️ Security Logs: Timer stopped (view hidden)")
