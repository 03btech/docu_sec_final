from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QMessageBox, QFrame, QScrollArea, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt
import qtawesome as qta
from api.client import APIClient

class SettingsView(QWidget):
    """User settings view - Regular users can only change password. Admins can edit profile."""
    
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.current_user = None
        self.is_admin = False
        self.departments = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_icon = qta.icon('fa5s.user-cog', color='#3498db')
        icon_label = QLabel()
        icon_label.setPixmap(title_icon.pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        title = QLabel("My Settings")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QLabel("Manage your account settings")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(subtitle)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #bdc3c7;")
        main_layout.addWidget(separator)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(20)
        
        # Profile Edit Section (Admin Only)
        self.profile_group = QGroupBox("Edit Profile")
        self.profile_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e4e7;
                border-radius: 10px;
                margin-top: 10px;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        profile_layout = QVBoxLayout()
        profile_layout.setSpacing(15)
        
        input_style = """
            QLineEdit, QComboBox {
                padding: 12px 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """
        
        # Email
        email_label = QLabel("Email Address:")
        email_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        profile_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        self.email_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.email_input)
        
        # First Name
        fname_label = QLabel("First Name:")
        fname_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        profile_layout.addWidget(fname_label)
        
        self.firstname_input = QLineEdit()
        self.firstname_input.setPlaceholderText("John")
        self.firstname_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.firstname_input)
        
        # Last Name
        lname_label = QLabel("Last Name:")
        lname_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        profile_layout.addWidget(lname_label)
        
        self.lastname_input = QLineEdit()
        self.lastname_input.setPlaceholderText("Doe")
        self.lastname_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.lastname_input)
        
        # Department
        dept_label = QLabel("Department:")
        dept_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        profile_layout.addWidget(dept_label)
        
        self.department_combo = QComboBox()
        self.department_combo.setStyleSheet(input_style)
        profile_layout.addWidget(self.department_combo)
        
        # Save Profile Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_profile_btn = QPushButton("Save Profile")
        save_profile_btn.setIcon(qta.icon('fa5s.save', color='white'))
        save_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        save_profile_btn.clicked.connect(self.update_profile)
        button_layout.addWidget(save_profile_btn)
        button_layout.addStretch()
        
        profile_layout.addLayout(button_layout)
        
        self.profile_group.setLayout(profile_layout)
        settings_layout.addWidget(self.profile_group)
        
        # User Information (Read-Only Display)
        info_group = QGroupBox("Your Profile")
        info_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e4e7;
                border-radius: 10px;
                margin-top: 10px;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(15)
        
        # Display user info
        self.username_label = QLabel()
        self.username_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        info_layout.addWidget(self.username_label)
        
        self.email_label = QLabel()
        self.email_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        info_layout.addWidget(self.email_label)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        info_layout.addWidget(self.name_label)
        
        self.dept_label = QLabel()
        self.dept_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        info_layout.addWidget(self.dept_label)
        
        self.role_label = QLabel()
        self.role_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        info_layout.addWidget(self.role_label)
        
        # Info message
        info_message = QLabel("ℹ️ To update your profile information (email, name, department), please contact an administrator.")
        info_message.setStyleSheet("""
            font-size: 13px;
            color: #16a085;
            padding: 12px;
            background-color: #d1f2eb;
            border-radius: 6px;
            border-left: 4px solid #16a085;
        """)
        info_message.setWordWrap(True)
        info_layout.addWidget(info_message)
        
        info_group.setLayout(info_layout)
        settings_layout.addWidget(info_group)
        
        # Change Password Section
        password_group = QGroupBox("Change Password")
        password_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e4e7;
                border-radius: 10px;
                margin-top: 10px;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        password_layout = QVBoxLayout()
        password_layout.setSpacing(15)
        
        input_style = """
            QLineEdit {
                padding: 12px 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """
        
        # Current Password
        current_pwd_label = QLabel("Current Password:")
        current_pwd_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        password_layout.addWidget(current_pwd_label)
        
        self.current_password_input = QLineEdit()
        self.current_password_input.setPlaceholderText("Enter your current password")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.current_password_input)
        
        # New Password
        new_pwd_label = QLabel("New Password:")
        new_pwd_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        password_layout.addWidget(new_pwd_label)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("Enter new password")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.new_password_input)
        
        # Confirm Password
        confirm_pwd_label = QLabel("Confirm New Password:")
        confirm_pwd_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34495e;")
        password_layout.addWidget(confirm_pwd_label)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm new password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.confirm_password_input)
        
        # Password requirements
        password_hint = QLabel("⚠️ Password must be at least 6 characters long")
        password_hint.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 4px;
        """)
        password_layout.addWidget(password_hint)
        
        # Change Password Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        change_pwd_btn = QPushButton("Change Password")
        change_pwd_btn.setIcon(qta.icon('fa5s.key', color='white'))
        change_pwd_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #ba4a00;
            }
        """)
        change_pwd_btn.clicked.connect(self.change_password)
        button_layout.addWidget(change_pwd_btn)
        button_layout.addStretch()
        
        password_layout.addLayout(button_layout)
        
        password_group.setLayout(password_layout)
        settings_layout.addWidget(password_group)
        
        settings_layout.addStretch()
        scroll.setWidget(settings_widget)
        main_layout.addWidget(scroll)
        
        # Load user data
        self.load_user_data()
    
    def load_user_data(self):
        """Load current user data for display."""
        self.current_user = self.api_client.get_current_user()
        if self.current_user:
            username = self.current_user.get('username', 'N/A')
            email = self.current_user.get('email', 'N/A')
            first_name = self.current_user.get('first_name', '')
            last_name = self.current_user.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or 'N/A'
            
            dept = self.current_user.get('department')
            dept_name = dept.get('name', 'None') if dept else 'None'
            dept_id = self.current_user.get('department_id')
            
            role = self.current_user.get('role', 'user').upper()
            self.is_admin = self.current_user.get('role', 'user') == 'admin'
            
            self.username_label.setText(f"👤 Username: {username}")
            self.email_label.setText(f"📧 Email: {email}")
            self.name_label.setText(f"📝 Full Name: {full_name}")
            self.dept_label.setText(f"🏢 Department: {dept_name}")
            self.role_label.setText(f"🔑 Role: {role}")
            
            # Show/hide profile edit section based on role
            if self.is_admin:
                self.profile_group.setVisible(True)
                self.load_departments()
                # Populate edit fields
                self.email_input.setText(email)
                self.firstname_input.setText(first_name)
                self.lastname_input.setText(last_name)
                # Set department
                if dept_id:
                    index = self.department_combo.findData(dept_id)
                    if index >= 0:
                        self.department_combo.setCurrentIndex(index)
            else:
                self.profile_group.setVisible(False)
    
    def load_departments(self):
        """Load departments from API."""
        try:
            self.departments = self.api_client.get_departments()
            self.department_combo.clear()
            self.department_combo.addItem("No Department", None)
            if self.departments:
                for dept in self.departments:
                    self.department_combo.addItem(dept['name'], dept['id'])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load departments: {e}")
    
    def update_profile(self):
        """Update profile information (admin only)."""
        if not self.is_admin:
            QMessageBox.warning(self, "Access Denied", 
                              "Only administrators can edit profile information.")
            return
        
        email = self.email_input.text().strip()
        first_name = self.firstname_input.text().strip()
        last_name = self.lastname_input.text().strip()
        department_id = self.department_combo.currentData()
        
        # Validation
        if not all([email, first_name, last_name]):
            QMessageBox.warning(self, "Validation Error", 
                              "Email, first name, and last name are required.")
            return
        
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter a valid email address.")
            return
        
        # Update profile via API
        success, message = self.api_client.update_profile(
            email=email,
            first_name=first_name,
            last_name=last_name,
            department_id=department_id
        )
        
        if success:
            QMessageBox.information(self, "Success", 
                                  "Your profile has been updated successfully!")
            self.load_user_data()  # Reload to show updated data
        else:
            QMessageBox.critical(self, "Error", 
                               f"Failed to update profile: {message}")
    
    def change_password(self):
        """Change user password."""
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            QMessageBox.warning(self, "Validation Error", 
                              "Please fill in all password fields.")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "Validation Error", 
                              "New passwords do not match.")
            return
        
        if len(new_password) < 6:
            QMessageBox.warning(self, "Validation Error", 
                              "New password must be at least 6 characters long.")
            return
        
        if new_password == current_password:
            QMessageBox.warning(self, "Validation Error", 
                              "New password must be different from current password.")
            return
        
        # Change password
        success, message = self.api_client.change_password(current_password, new_password)
        
        if success:
            QMessageBox.information(self, "Success", 
                                  "Your password has been changed successfully!")
            # Clear password fields
            self.current_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
        else:
            QMessageBox.critical(self, "Error", 
                               f"Failed to change password: {message}")
    
    def refresh_data(self):
        """Refresh view data when tab is shown."""
        self.load_user_data()
