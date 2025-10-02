from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel, QPushButton, QFrame, QStyle
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont
import qtawesome as qta
from api.client import APIClient
from views.dashboard_view import DashboardView
from views.my_documents_view import MyDocumentsView
from views.department_documents_view import DepartmentDocumentsView
from views.public_documents_view import PublicDocumentsView
from views.shared_documents_view import SharedDocumentsView
from views.upload_document_view import UploadDocumentView
from views.access_logs_view import AccessLogsView
from views.security_logs_view import SecurityLogsView
from views.settings_view_new import SettingsView
from views.user_management_view import UserManagementView

# Global reference to keep the window alive after logout/login
_active_main_window = None

class MainWindow(QMainWindow):
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.current_user = None
        self.setWindowTitle("Document Security - Main Window")
        self.setGeometry(100, 100, 1200, 800)
        try:
            self.setup_ui()
            self.load_user_info()
            self.show_dashboard()
        except Exception as e:
            print(f"Error in MainWindow init: {e}")
            import traceback
            traceback.print_exc()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Navigation Panel (Left)
        self.nav_panel = QWidget()
        self.nav_panel.setFixedWidth(350)
        nav_layout = QVBoxLayout(self.nav_panel)

        # Add a title for the sidebar
        sidebar_title = QLabel("📂 DocuSec")
        sidebar_title.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 8px;
        """)
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(sidebar_title)

        # User Info Card
        self.user_info_widget = QWidget()
        self.user_info_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 2px solid #3498db;
                padding: 15px;
            }
        """)
        user_info_layout = QVBoxLayout(self.user_info_widget)
        user_info_layout.setSpacing(8)
        
        # Username
        self.username_label = QLabel()
        self.username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
        """)
        user_info_layout.addWidget(self.username_label)
        
        # Email
        self.email_label = QLabel()
        self.email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_label.setWordWrap(True)
        self.email_label.setStyleSheet("""
            font-size: 11px;
            color: #7f8c8d;
        """)
        user_info_layout.addWidget(self.email_label)
        
        # Department
        self.dept_label = QLabel()
        self.dept_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dept_label.setWordWrap(True)
        self.dept_label.setStyleSheet("""
            font-size: 12px;
            color: #34495e;
            background-color: #ecf0f1;
            padding: 5px;
            border-radius: 5px;
        """)
        user_info_layout.addWidget(self.dept_label)
        
        # Role badge (will be shown/hidden based on role)
        self.role_label = QLabel()
        self.role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label.setWordWrap(True)
        self.role_label.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: white;
            background-color: #e74c3c;
            padding: 5px;
            border-radius: 5px;
        """)
        self.role_label.hide()  # Hidden by default
        user_info_layout.addWidget(self.role_label)
        
        nav_layout.addWidget(self.user_info_widget)

        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #bdc3c7;")
        nav_layout.addWidget(separator)

        # Navigation Buttons
        nav_label = QLabel("Navigation")
        nav_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #7f8c8d;
            padding: 5px 0px;
        """)
        nav_layout.addWidget(nav_label)
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setRootIsDecorated(True)
        
        # Create top-level items with Font Awesome icons
        # Dashboard item (admin-only)
        self.dashboard_item = QTreeWidgetItem(self.nav_tree)
        self.dashboard_item.setText(0, "Dashboard")
        self.dashboard_item.setIcon(0, qta.icon('fa5s.chart-line', color='#3498db'))
        
        documents_item = QTreeWidgetItem(self.nav_tree)
        documents_item.setText(0, "Documents")
        documents_item.setIcon(0, qta.icon('fa5s.folder', color='#f39c12'))
        
        # Add document sub-items
        my_docs_item = QTreeWidgetItem(documents_item)
        my_docs_item.setText(0, "My Documents")
        my_docs_item.setIcon(0, qta.icon('fa5s.file-alt', color='#9b59b6'))
        
        dept_docs_item = QTreeWidgetItem(documents_item)
        dept_docs_item.setText(0, "Department Documents")
        dept_docs_item.setIcon(0, qta.icon('fa5s.folder-open', color='#e67e22'))
        
        public_docs_item = QTreeWidgetItem(documents_item)
        public_docs_item.setText(0, "Public Documents")
        public_docs_item.setIcon(0, qta.icon('fa5s.globe', color='#16a085'))
        
        shared_docs_item = QTreeWidgetItem(documents_item)
        shared_docs_item.setText(0, "Shared With Me")
        shared_docs_item.setIcon(0, qta.icon('fa5s.share-alt', color='#27ae60'))
        
        upload_item = QTreeWidgetItem(documents_item)
        upload_item.setText(0, "Upload Document")
        upload_item.setIcon(0, qta.icon('fa5s.cloud-upload-alt', color='#2ecc71'))
        
        # Admin section (will be shown/hidden based on role)
        self.admin_item = QTreeWidgetItem(self.nav_tree)
        self.admin_item.setText(0, "Administration")
        self.admin_item.setIcon(0, qta.icon('fa5s.user-shield', color='#e74c3c'))
        
        # Logs parent item (admin-only)
        self.logs_item = QTreeWidgetItem(self.admin_item)
        self.logs_item.setText(0, "System Logs")
        self.logs_item.setIcon(0, qta.icon('fa5s.clipboard-list', color='#e74c3c'))
        
        # Add log sub-items
        self.access_logs_item = QTreeWidgetItem(self.logs_item)
        self.access_logs_item.setText(0, "Access Logs")
        self.access_logs_item.setIcon(0, qta.icon('fa5s.user-check', color='#3498db'))
        
        self.security_logs_item = QTreeWidgetItem(self.logs_item)
        self.security_logs_item.setText(0, "Security Logs")
        self.security_logs_item.setIcon(0, qta.icon('fa5s.shield-alt', color='#c0392b'))
        
        # Settings item (available to all users)
        settings_item = QTreeWidgetItem(self.nav_tree)
        settings_item.setText(0, "Settings")
        settings_item.setIcon(0, qta.icon('fa5s.user-cog', color='#95a5a6'))
        
        # User Management (admin-only, separate from Settings)
        self.user_mgmt_item = QTreeWidgetItem(self.nav_tree)
        self.user_mgmt_item.setText(0, "User Management")
        self.user_mgmt_item.setIcon(0, qta.icon('fa5s.users-cog', color='#e74c3c'))
        
        self.nav_tree.expandAll()
        self.nav_tree.itemClicked.connect(self.change_view)
        # Set minimum height to ensure navigation items are not cramped
        self.nav_tree.setMinimumHeight(400)
        nav_layout.addWidget(self.nav_tree, stretch=1)

        # Logout Button
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout)
        nav_layout.addWidget(self.logout_button)

        # Minimal stretch to push logout to bottom but give priority to nav_tree
        nav_layout.addStretch(0)
        main_layout.addWidget(self.nav_panel)

        # Content Area (Right)
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        # Add views
        self.dashboard_view = DashboardView(self.api_client)
        self.content_stack.addWidget(self.dashboard_view)

        self.my_documents_view = MyDocumentsView(self.api_client)
        self.content_stack.addWidget(self.my_documents_view)

        self.department_documents_view = DepartmentDocumentsView(self.api_client)
        self.content_stack.addWidget(self.department_documents_view)

        self.public_documents_view = PublicDocumentsView(self.api_client)
        self.content_stack.addWidget(self.public_documents_view)

        self.shared_documents_view = SharedDocumentsView(self.api_client)
        self.content_stack.addWidget(self.shared_documents_view)

        self.upload_document_view = UploadDocumentView(self.api_client)
        self.content_stack.addWidget(self.upload_document_view)

        # Log views (index 6, 7)
        self.access_logs_view = AccessLogsView(self.api_client)
        self.content_stack.addWidget(self.access_logs_view)

        self.security_logs_view = SecurityLogsView(self.api_client)
        self.content_stack.addWidget(self.security_logs_view)
        
        # Settings view (index 9) - available to all users
        self.settings_view = SettingsView(self.api_client)
        self.content_stack.addWidget(self.settings_view)
        
        # User Management view (index 10) - admin only
        self.user_management_view = UserManagementView(self.api_client)
        self.content_stack.addWidget(self.user_management_view)

        # Placeholder for other views (if needed)
        # for i in range(0):
        #     placeholder = QLabel(f"View {i+8} - Coming Soon")
        #     placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #     self.content_stack.addWidget(placeholder)

        # Adjust layout for better spacing and alignment
        nav_layout.setSpacing(12)
        nav_layout.setContentsMargins(15, 15, 15, 15)

        # Adjust the appearance of the navigation tree
        self.nav_tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #2c3e50;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 8px;
                border-radius: 8px;
                margin: 2px 0px;
            }
            QTreeWidget::item:hover {
                background-color: #ecf0f1;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
        """)

        # Enable vertical scrolling when needed, disable horizontal
        self.nav_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Adjust the logout button style
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
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
        
        # Set navigation panel background
        self.nav_panel.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
        """)

    def load_user_info(self):
        """Load and display current user information."""
        self.current_user = self.api_client.get_current_user()
        if self.current_user:
            # Get user details
            username = self.current_user.get('username', 'User')
            first_name = self.current_user.get('first_name', '')
            last_name = self.current_user.get('last_name', '')
            email = self.current_user.get('email', 'No email')
            role = self.current_user.get('role', 'user')
            
            # Display full name if available, otherwise username
            if first_name and last_name:
                display_name = f"{first_name} {last_name}"
            elif first_name:
                display_name = first_name
            else:
                display_name = username
            
            self.username_label.setText(display_name)
            self.email_label.setText(email)
            
            # Show role badge if admin
            if role == 'admin':
                self.role_label.setText("👑 ADMINISTRATOR")
                self.role_label.show()
            else:
                self.role_label.hide()
            
            # Get department name
            dept_name = "No Department"
            dept_id = self.current_user.get("department_id")
            if dept_id:
                # Try to fetch department info
                departments = self.api_client.get_departments()
                for dept in departments:
                    if dept.get('id') == dept_id:
                        dept_name = dept.get('name', f'Department {dept_id}')
                        break
                if dept_name == "No Department":
                    dept_name = f"Department #{dept_id}"
            
            dept_icon = qta.icon('fa5s.building', color='#95a5a6', scale_factor=0.8)
            self.dept_label.setText(f"  {dept_name}")
            
            # Add icon to department label if needed
            self.dept_label.setStyleSheet("""
                font-size: 12px;
                color: #34495e;
                background-color: #ecf0f1;
                padding: 6px 10px;
                border-radius: 5px;
                font-weight: 500;
            """)
            
            # Show/hide admin navigation based on role
            self.admin_item.setHidden(role != 'admin')
            # Show/hide dashboard based on role (admin-only)
            self.dashboard_item.setHidden(role != 'admin')
            # Show/hide User Management based on role (admin-only)
            self.user_mgmt_item.setHidden(role != 'admin')
            
        else:
            self.username_label.setText("Guest User")
            self.email_label.setText("Not logged in")
            self.dept_label.setText("No Department")
            self.role_label.hide()
            # Hide admin section for non-logged-in users
            self.admin_item.setHidden(True)
            # Hide dashboard for non-logged-in users
            self.dashboard_item.setHidden(True)
            # Hide User Management for non-logged-in users
            self.user_mgmt_item.setHidden(True)

    def change_view(self, item, column):
        text = item.text(0)
        if text == "Dashboard":
            # Check if user is admin
            if self.api_client.is_admin():
                self.content_stack.setCurrentIndex(0)
                self.dashboard_view.refresh_data()
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Access Denied", "Only administrators can access the dashboard.")
        elif text == "My Documents":
            self.content_stack.setCurrentIndex(1)
            self.my_documents_view.refresh_data()
        elif text == "Department Documents":
            self.content_stack.setCurrentIndex(2)
            self.department_documents_view.refresh_data()
        elif text == "Public Documents":
            self.content_stack.setCurrentIndex(3)
            self.public_documents_view.refresh_data()
        elif text == "Shared With Me":
            self.content_stack.setCurrentIndex(4)
            self.shared_documents_view.refresh_data()
        elif text == "Upload Document":
            self.content_stack.setCurrentIndex(5)
            # Upload view doesn't need refreshing
        elif text == "Access Logs":
            # Check if user is admin
            if self.api_client.is_admin():
                self.content_stack.setCurrentIndex(6)
                self.access_logs_view.refresh_data()
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Access Denied", "Only administrators can view access logs.")
        elif text == "Security Logs":
            # Check if user is admin
            if self.api_client.is_admin():
                self.content_stack.setCurrentIndex(7)
                self.security_logs_view.refresh_data()
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Access Denied", "Only administrators can view security logs.")
        elif text == "Settings":
            self.content_stack.setCurrentIndex(8)
            self.settings_view.refresh_data()
        elif text == "User Management":
            # Check if user is admin (this is now the standalone User Management, not under admin section)
            if self.api_client.is_admin():
                self.content_stack.setCurrentIndex(9)
                self.user_management_view.refresh_data()
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Access Denied", "Only administrators can access user management.")

    def show_dashboard(self):
        # Only show dashboard if user is admin, otherwise show My Documents
        if self.api_client.is_admin():
            self.nav_tree.setCurrentItem(self.dashboard_item)
            self.dashboard_view.refresh_data()
        else:
            # Navigate to My Documents for regular users
            self.content_stack.setCurrentIndex(1)
            self.my_documents_view.refresh_data()

    def logout(self):
        global _active_main_window
        from views.login_window import LoginWindow
        
        # Stop all auto-refresh timers before logout
        try:
            if hasattr(self.access_logs_view, 'auto_refresh_timer'):
                self.access_logs_view.auto_refresh_timer.stop()
            if hasattr(self.security_logs_view, 'auto_refresh_timer'):
                self.security_logs_view.auto_refresh_timer.stop()
            if hasattr(self.dashboard_view, 'auto_refresh_timer'):
                self.dashboard_view.auto_refresh_timer.stop()
        except Exception as e:
            print(f"Warning: Error stopping timers: {e}")
        
        # Logout from API (clear session)
        self.api_client.logout()
        
        # Store reference to prevent garbage collection
        self.login_window = LoginWindow(self.api_client)
        
        def on_login_successful():
            global _active_main_window
            # Create new main window and store globally to prevent garbage collection
            _active_main_window = MainWindow(self.api_client)
            _active_main_window.show()
            _active_main_window.raise_()
            _active_main_window.activateWindow()
            # Close login window
            self.login_window.close()
        
        self.login_window.login_successful.connect(on_login_successful)
        
        # Show login window and close current main window
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()
        self.close()
