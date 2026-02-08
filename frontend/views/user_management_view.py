from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QMessageBox, QComboBox, QFrame, QScrollArea, 
                             QTableWidget, QTableWidgetItem, QDialog, QDialogButtonBox, 
                             QGroupBox, QHeaderView, QMenu, QTabWidget, QInputDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
import qtawesome as qta
from api.client import APIClient
from views.admin_user_management_view import AdminUserManagementView


class UserActionMenuButton(QPushButton):
    """Custom button that shows a dropdown menu with user actions"""
    
    def __init__(self, user_data: dict, parent_view, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.parent_view = parent_view
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
        
        # Add Edit action
        edit_action = menu.addAction(
            qta.icon('fa5s.edit', color='#3b82f6'), 
            "Edit User"
        )
        edit_action.triggered.connect(lambda: self.parent_view.edit_user(self.user_data))
        
        # Add separator
        menu.addSeparator()
        
        # Add Delete action
        delete_action = menu.addAction(
            qta.icon('fa5s.trash-alt', color='#ef4444'), 
            "Delete User"
        )
        delete_action.triggered.connect(lambda: self.parent_view.delete_user(self.user_data))
        
        # Show menu at button position
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))


class RoleBadge(QWidget):
    """Custom widget for role badges with color coding"""
    
    ROLE_COLORS = {
        'admin': ('#ef4444', '#fee2e2'),  # Red
        'user': ('#3b82f6', '#dbeafe'),   # Blue
    }
    
    def __init__(self, role: str, parent=None):
        super().__init__(parent)
        self.role = role.lower()
        self.setMinimumHeight(40)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Get colors for role
        text_color, bg_color = self.ROLE_COLORS.get(
            self.role, 
            ('#6b7280', '#f3f4f6')  # Gray for unknown
        )
        
        # Create badge label
        badge = QLabel(self.role.upper())
        badge.setMinimumHeight(24)
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


class UserEditDialog(QDialog):
    """Dialog for editing user details."""
    
    def __init__(self, api_client: APIClient, user_data: dict, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.user_data = user_data
        self.departments = []
        self.setWindowTitle(f"Edit User: {user_data['username']}")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.setup_ui()
        self.load_departments()
        self.load_user_data()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        self.resize(500, 600)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        
        # Input style
        input_style = """
            QLineEdit, QComboBox {
                padding: 10px 15px;
                border: 2px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
        """
        
        # Username
        username_label = QLabel("Username:")
        username_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setStyleSheet(input_style)
        layout.addWidget(self.username_input)
        
        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        self.email_input.setStyleSheet(input_style)
        layout.addWidget(self.email_input)
        
        # First Name
        fname_label = QLabel("First Name:")
        fname_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(fname_label)
        
        self.fname_input = QLineEdit()
        self.fname_input.setPlaceholderText("Enter first name")
        self.fname_input.setStyleSheet(input_style)
        layout.addWidget(self.fname_input)
        
        # Last Name
        lname_label = QLabel("Last Name:")
        lname_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(lname_label)
        
        self.lname_input = QLineEdit()
        self.lname_input.setPlaceholderText("Enter last name")
        self.lname_input.setStyleSheet(input_style)
        layout.addWidget(self.lname_input)
        
        # Department
        dept_label = QLabel("Department:")
        dept_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(dept_label)
        
        self.dept_combo = QComboBox()
        self.dept_combo.setStyleSheet(input_style)
        layout.addWidget(self.dept_combo)
        
        # Role
        role_label = QLabel("Role:")
        role_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(role_label)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["user", "admin"])
        self.role_combo.setStyleSheet(input_style)
        layout.addWidget(self.role_combo)
        
        # Password Reset Section
        password_group = QGroupBox("Reset Password")
        password_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e0e4e7;
                border-radius: 6px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        password_layout = QVBoxLayout()
        
        password_note = QLabel("Leave blank to keep current password")
        password_note.setStyleSheet("color: #7f8c8d; font-size: 12px; font-weight: normal;")
        password_layout.addWidget(password_note)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("New password (optional)")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.new_password_input)
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # Add stretch to push content up
        layout.addStretch()
        
        # Set scroll widget
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        
        # Style buttons
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        main_layout.addWidget(button_box)
    
    def load_departments(self):
        """Load departments into combo box."""
        self.departments = self.api_client.get_departments()
        self.dept_combo.clear()
        self.dept_combo.addItem("None", None)
        for dept in self.departments:
            self.dept_combo.addItem(dept['name'], dept['id'])
    
    def load_user_data(self):
        """Load user data into form."""
        self.username_input.setText(self.user_data.get('username', ''))
        self.email_input.setText(self.user_data.get('email', ''))
        self.fname_input.setText(self.user_data.get('first_name', ''))
        self.lname_input.setText(self.user_data.get('last_name', ''))
        
        # Set department
        dept_id = self.user_data.get('department_id')
        if dept_id:
            index = self.dept_combo.findData(dept_id)
            if index >= 0:
                self.dept_combo.setCurrentIndex(index)
        
        # Set role
        role = self.user_data.get('role', 'user')
        index = self.role_combo.findText(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
    
    def save_user(self):
        """Save user changes."""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        first_name = self.fname_input.text().strip()
        last_name = self.lname_input.text().strip()
        role = self.role_combo.currentText()
        dept_id = self.dept_combo.currentData()
        new_password = self.new_password_input.text()
        
        # Validation
        if not all([username, email, first_name, last_name]):
            QMessageBox.warning(self, "Validation Error", 
                              "Username, email, first name, and last name are required.")
            return
        
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter a valid email address.")
            return
        
        # Update user
        user_id = self.user_data['id']
        success, message = self.api_client.admin_update_user(
            user_id, email, first_name, last_name, username, role, dept_id
        )
        
        if not success:
            QMessageBox.critical(self, "Error", f"Failed to update user: {message}")
            return
        
        # Reset password if provided
        if new_password:
            if len(new_password) < 6:
                QMessageBox.warning(self, "Validation Error", 
                                  "Password must be at least 6 characters long.")
                return
            
            success, message = self.api_client.admin_reset_password(user_id, new_password)
            if not success:
                QMessageBox.warning(self, "Warning", 
                                  f"User updated but password reset failed: {message}")
        
        QMessageBox.information(self, "Success", "User updated successfully!")
        self.accept()


class UserManagementView(QWidget):
    """Admin view for managing all users."""
    
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.users = []
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Title
        title = QLabel("User Management")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #1f2937;
            }
        """)
        header_layout.addWidget(title)
        
        # Description
        description = QLabel("Manage user accounts and departments")
        description.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6b7280;
            }
        """)
        header_layout.addWidget(description)
        
        main_layout.addWidget(header_widget)

        # Tab widget for Users / Departments
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                color: #6b7280;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                color: #27ae60;
                border-bottom: 2px solid #27ae60;
            }
            QTabBar::tab:hover:!selected {
                color: #374151;
            }
        """)
        main_layout.addWidget(self.tab_widget)

        # ── Users Tab ──
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        users_layout.setContentsMargins(0, 12, 0, 0)
        users_layout.setSpacing(12)

        self._setup_users_tab(users_layout)
        self.tab_widget.addTab(users_tab, qta.icon('fa5s.users', color='#6b7280'), "Users")

        # ── Departments Tab ──
        dept_tab = QWidget()
        dept_layout = QVBoxLayout(dept_tab)
        dept_layout.setContentsMargins(0, 12, 0, 0)
        dept_layout.setSpacing(12)

        self._setup_departments_tab(dept_layout)
        self.tab_widget.addTab(dept_tab, qta.icon('fa5s.building', color='#6b7280'), "Departments")

        # Load initial data
        self.refresh_users()
        self.refresh_departments()

    # ──────────────────────────────────────────────
    # Users tab setup
    # ──────────────────────────────────────────────
    def _setup_users_tab(self, layout):
        
        # Action bar with search
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by username, email, or name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 16px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.search_input.textChanged.connect(self.search_users)
        action_bar.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.setIcon(qta.icon('fa5s.search', color='#374151'))
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
        """)
        search_btn.clicked.connect(self.refresh_users)
        action_bar.addWidget(search_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync-alt', color='#374151'))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.refresh_users(clear_search=True))
        action_bar.addWidget(refresh_btn)
        
        # Create User button (admin only)
        create_user_btn = QPushButton("Create User")
        create_user_btn.setIcon(qta.icon('fa5s.user-plus', color="white"))
        create_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        create_user_btn.clicked.connect(self.create_user)
        action_bar.addWidget(create_user_btn)
        
        action_bar.addStretch()
        
        layout.addLayout(action_bar)
        
        # Users table with modern styling
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels([
            "Username", "Email", "Name", "Department", "Role", ""
        ])
        
        # Hide row numbers
        vertical_header = self.users_table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        
        # Set table properties
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.users_table.setAlternatingRowColors(False)
        self.users_table.setShowGrid(False)
        
        # Set fixed row height
        v_header = self.users_table.verticalHeader()
        if v_header:
            v_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            v_header.setDefaultSectionSize(60)
        
        # Configure column behavior
        header = self.users_table.horizontalHeader()
        if header:
            # Username - interactive
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self.users_table.setColumnWidth(0, 150)
            # Email - stretch
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            # Name - interactive
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            self.users_table.setColumnWidth(2, 180)
            # Department - interactive
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.users_table.setColumnWidth(3, 150)
            # Role - fixed
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.users_table.setColumnWidth(4, 120)
            # Actions - fixed
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
            self.users_table.setColumnWidth(5, 60)
        
        # Apply modern styling
        self.users_table.setStyleSheet("""
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
                color: #1f2937;
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
        
        layout.addWidget(self.users_table)
    
    def refresh_users(self, clear_search=False):
        """Refresh the users list."""
        if clear_search:
            self.search_input.clear()
        
        search = self.search_input.text().strip() or None
        self.users = self.api_client.get_users(search)
        self.populate_table()
    
    def search_users(self):
        """Search users as user types."""
        # Debounce or search on demand
        pass
    
    def populate_table(self):
        """Populate table with users."""
        self.users_table.setRowCount(0)
        
        for user in self.users:
            row = self.users_table.rowCount()
            self.users_table.insertRow(row)
            
            # Set row height explicitly for each row
            self.users_table.setRowHeight(row, 60)
            
            # Column 0: Username with icon
            username_widget = QWidget()
            username_layout = QHBoxLayout(username_widget)
            username_layout.setContentsMargins(12, 0, 0, 0)
            username_layout.setSpacing(8)
            
            # User icon
            icon_label = QLabel()
            user_icon = qta.icon('fa5s.user-circle', color='#6b7280')
            icon_label.setPixmap(user_icon.pixmap(24, 24))
            username_layout.addWidget(icon_label)
            
            # Username text
            username_label = QLabel(user.get('username', ''))
            username_label.setStyleSheet("""
                font-size: 14px;
                font-weight: 600;
                color: #1f2937;
            """)
            username_layout.addWidget(username_label)
            username_layout.addStretch()
            
            self.users_table.setCellWidget(row, 0, username_widget)
            
            # Column 1: Email
            email_item = QTableWidgetItem(user.get('email', ''))
            email_item.setForeground(QColor('#6b7280'))
            email_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row, 1, email_item)
            
            # Column 2: Name
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            name_item = QTableWidgetItem(full_name)
            name_item.setForeground(QColor('#6b7280'))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row, 2, name_item)
            
            # Column 3: Department
            dept_name = user.get('department', {}).get('name', 'None') if user.get('department') else 'None'
            dept_item = QTableWidgetItem(dept_name)
            dept_item.setForeground(QColor('#6b7280'))
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row, 3, dept_item)
            
            # Column 4: Role badge
            role = user.get('role', 'user')
            role_badge = RoleBadge(role)
            self.users_table.setCellWidget(row, 4, role_badge)
            
            # Column 5: Action menu button
            action_button = UserActionMenuButton(user, self)
            
            # Center the button in cell
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(action_button)
            button_layout.addStretch()
            
            self.users_table.setCellWidget(row, 5, button_container)
    
    def edit_user(self, user):
        """Open edit dialog for user."""
        dialog = UserEditDialog(self.api_client, user, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_users()
    
    def delete_user(self, user):
        """Delete a user."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete user '{user['username']}'?\n\n"
            "This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.api_client.admin_delete_user(user['id'])
            if success:
                QMessageBox.information(self, "Success", "User deleted successfully!")
                self.refresh_users()
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {message}")
    
    def create_user(self):
        """Open create user dialog."""
        dialog = AdminUserManagementView(self.api_client)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Success", "User created successfully!")
            self.refresh_users()
    
    def refresh_data(self):
        """Refresh view data when tab is shown."""
        self.refresh_users()
        self.refresh_departments()

    # ──────────────────────────────────────────────
    # Departments tab
    # ──────────────────────────────────────────────
    def _setup_departments_tab(self, layout):
        # Action bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)

        add_dept_btn = QPushButton("  Add Department")
        add_dept_btn.setIcon(qta.icon('fa5s.plus', color='white'))
        add_dept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_dept_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        add_dept_btn.clicked.connect(self.add_department)
        action_bar.addWidget(add_dept_btn)

        action_bar.addStretch()

        refresh_dept_btn = QPushButton("Refresh")
        refresh_dept_btn.setIcon(qta.icon('fa5s.sync-alt', color='#374151'))
        refresh_dept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_dept_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { background-color: #f9fafb; border-color: #9ca3af; }
        """)
        refresh_dept_btn.clicked.connect(self.refresh_departments)
        action_bar.addWidget(refresh_dept_btn)

        layout.addLayout(action_bar)

        # Departments table
        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(3)
        self.dept_table.setHorizontalHeaderLabels(["ID", "Department Name", ""])

        vh = self.dept_table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            vh.setDefaultSectionSize(50)

        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dept_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dept_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.dept_table.setShowGrid(False)

        hh = self.dept_table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.dept_table.setColumnWidth(0, 60)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.dept_table.setColumnWidth(2, 140)

        self.dept_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff; border: 1px solid #e5e7eb;
                border-radius: 8px; gridline-color: transparent;
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
        layout.addWidget(self.dept_table)

    def refresh_departments(self):
        """Reload departments into the table."""
        self.departments = self.api_client.get_departments()
        self.dept_table.setRowCount(0)
        for dept in self.departments:
            row = self.dept_table.rowCount()
            self.dept_table.insertRow(row)
            self.dept_table.setRowHeight(row, 50)

            # ID
            id_item = QTableWidgetItem(str(dept['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setForeground(QColor('#6b7280'))
            self.dept_table.setItem(row, 0, id_item)

            # Name
            name_item = QTableWidgetItem(dept['name'])
            name_item.setForeground(QColor('#1f2937'))
            self.dept_table.setItem(row, 1, name_item)

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)

            edit_btn = QPushButton()
            edit_btn.setIcon(qta.icon('fa5s.edit', color='#3b82f6'))
            edit_btn.setToolTip("Rename")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setFixedSize(32, 32)
            edit_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 6px; }
                QPushButton:hover { background-color: #dbeafe; }
            """)
            dept_id = dept['id']
            dept_name = dept['name']
            edit_btn.clicked.connect(lambda checked, d=dept_id, n=dept_name: self.rename_department(d, n))
            actions_layout.addWidget(edit_btn)

            del_btn = QPushButton()
            del_btn.setIcon(qta.icon('fa5s.trash-alt', color='#ef4444'))
            del_btn.setToolTip("Delete")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 6px; }
                QPushButton:hover { background-color: #fee2e2; }
            """)
            del_btn.clicked.connect(lambda checked, d=dept_id, n=dept_name: self.delete_department(d, n))
            actions_layout.addWidget(del_btn)

            actions_layout.addStretch()
            self.dept_table.setCellWidget(row, 2, actions_widget)

    def add_department(self):
        """Prompt for a department name and create it."""
        name, ok = QInputDialog.getText(self, "Add Department", "Department name:")
        if ok and name.strip():
            success, msg = self.api_client.create_department(name.strip())
            if success:
                self.refresh_departments()
            else:
                QMessageBox.critical(self, "Error", f"Failed to create department: {msg}")

    def rename_department(self, dept_id: int, current_name: str):
        """Prompt for new name and update."""
        name, ok = QInputDialog.getText(self, "Rename Department", "New name:", text=current_name)
        if ok and name.strip() and name.strip() != current_name:
            success, msg = self.api_client.update_department(dept_id, name.strip())
            if success:
                self.refresh_departments()
            else:
                QMessageBox.critical(self, "Error", f"Failed to rename department: {msg}")

    def delete_department(self, dept_id: int, name: str):
        """Confirm and delete a department."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete department '{name}'?\n\nAll users in this department will be unassigned.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.api_client.delete_department(dept_id)
            if success:
                self.refresh_departments()
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete department: {msg}")
