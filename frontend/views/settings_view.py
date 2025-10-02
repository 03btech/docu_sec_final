from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QMessageBox, QComboBox, QFrame, QScrollArea, QGroupBox)
from PyQt6.QtCore import Qt
import qtawesome as qta
from api.client import APIClient

class SettingsView(QWidget):
    """User settings and profile configuration view."""
    
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.current_user = None
        self.departments = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_icon = qta.icon('fa5s.cog', color='#3498db')
        icon_label = QLabel()
        icon_label.setPixmap(title_icon.pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        title = QLabel("Settings")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QLabel("Manage your account settings and profile information")
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
        
        # Profile Information Section
        profile_group = QGroupBox("Profile Information")
        profile_group.setStyleSheet("""
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
            QLineEdit:read-only {
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """
        
        # Username (read-only)
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setReadOnly(True)
        self.username_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.username_input)
        
        # Email
        email_label = QLabel("Email Address")
        email_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        self.email_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.email_input)
        
        # First Name
        fname_label = QLabel("First Name")
        fname_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(fname_label)
        
        self.firstname_input = QLineEdit()
        self.firstname_input.setPlaceholderText("John")
        self.firstname_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.firstname_input)
        
        # Last Name
        lname_label = QLabel("Last Name")
        lname_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(lname_label)
        
        self.lastname_input = QLineEdit()
        self.lastname_input.setPlaceholderText("Doe")
        self.lastname_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.lastname_input)
        
        # Department
        dept_label = QLabel("Department")
        dept_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(dept_label)
        
        self.department_combo = QComboBox()
        self.department_combo.setStyleSheet(input_style)
        profile_layout.addWidget(self.department_combo)
        
        # Role (read-only)
        role_label = QLabel("Role")
        role_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        profile_layout.addWidget(role_label)
        
        self.role_input = QLineEdit()
        self.role_input.setReadOnly(True)
        self.role_input.setStyleSheet(input_style)
        profile_layout.addWidget(self.role_input)
        
        # Update Profile Button
        update_profile_btn = QPushButton("Update Profile")
        update_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
        """)
        update_profile_btn.clicked.connect(self.update_profile)
        profile_layout.addWidget(update_profile_btn)
        
        profile_group.setLayout(profile_layout)
        settings_layout.addWidget(profile_group)
        
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
        
        # Current Password
        current_pwd_label = QLabel("Current Password")
        current_pwd_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        password_layout.addWidget(current_pwd_label)
        
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setPlaceholderText("Enter current password")
        self.current_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.current_password_input)
        
        # New Password
        new_pwd_label = QLabel("New Password")
        new_pwd_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        password_layout.addWidget(new_pwd_label)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("Enter new password")
        self.new_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.new_password_input)
        
        # Confirm New Password
        confirm_pwd_label = QLabel("Confirm New Password")
        confirm_pwd_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        password_layout.addWidget(confirm_pwd_label)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Re-enter new password")
        self.confirm_password_input.setStyleSheet(input_style)
        password_layout.addWidget(self.confirm_password_input)
        
        # Password info
        pwd_info = QLabel("Password must be at least 6 characters long")
        pwd_info.setStyleSheet("""
            color: #7f8c8d;
            font-size: 12px;
            font-style: italic;
        """)
        password_layout.addWidget(pwd_info)
        
        # Change Password Button
        change_pwd_btn = QPushButton("Change Password")
        change_pwd_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
            QPushButton:pressed { background-color: #ba4a00; }
        """)
        change_pwd_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_pwd_btn)
        
        password_group.setLayout(password_layout)
        settings_layout.addWidget(password_group)
        
        settings_layout.addStretch()
        
        scroll.setWidget(settings_widget)
        main_layout.addWidget(scroll)

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
            print(f"Error loading departments: {e}")

    def load_user_data(self):
        """Load current user data into form."""
        try:
            self.current_user = self.api_client.get_current_user()
            if self.current_user:
                self.username_input.setText(self.current_user.get('username', ''))
                self.email_input.setText(self.current_user.get('email', ''))
                self.firstname_input.setText(self.current_user.get('first_name', ''))
                self.lastname_input.setText(self.current_user.get('last_name', ''))
                
                # Set role
                role = self.current_user.get('role', 'user')
                role_display = "Administrator" if role == 'admin' else "Regular User"
                self.role_input.setText(role_display)
                
                # Set department
                dept_id = self.current_user.get('department_id')
                if dept_id:
                    for i in range(self.department_combo.count()):
                        if self.department_combo.itemData(i) == dept_id:
                            self.department_combo.setCurrentIndex(i)
                            break
                else:
                    self.department_combo.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load user data: {e}")

    def update_profile(self):
        """Update user profile information."""
        email = self.email_input.text().strip()
        firstname = self.firstname_input.text().strip()
        lastname = self.lastname_input.text().strip()
        department_id = self.department_combo.currentData()
        
        if not all([email, firstname, lastname]):
            QMessageBox.warning(self, "Validation Error", "Please fill in all profile fields.")
            return
        
        # Validate email format
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return
        
        try:
            success, message = self.api_client.update_profile(
                email=email,
                first_name=firstname,
                last_name=lastname,
                department_id=department_id
            )
            
            if success:
                QMessageBox.information(
                    self, 
                    "Success", 
                    "Your profile has been updated successfully!"
                )
                self.load_user_data()  # Reload to show updated data
            else:
                QMessageBox.warning(self, "Update Failed", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while updating profile:\n{str(e)}")

    def change_password(self):
        """Change user password."""
        current_pwd = self.current_password_input.text()
        new_pwd = self.new_password_input.text()
        confirm_pwd = self.confirm_password_input.text()
        
        if not all([current_pwd, new_pwd, confirm_pwd]):
            QMessageBox.warning(self, "Validation Error", "Please fill in all password fields.")
            return
        
        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Validation Error", "New passwords do not match.")
            return
        
        if len(new_pwd) < 6:
            QMessageBox.warning(self, "Validation Error", "New password must be at least 6 characters long.")
            return
        
        if current_pwd == new_pwd:
            QMessageBox.warning(self, "Validation Error", "New password must be different from current password.")
            return
        
        try:
            success, message = self.api_client.change_password(
                current_password=current_pwd,
                new_password=new_pwd
            )
            
            if success:
                QMessageBox.information(
                    self, 
                    "Success", 
                    "Your password has been changed successfully!"
                )
                # Clear password fields
                self.current_password_input.clear()
                self.new_password_input.clear()
                self.confirm_password_input.clear()
            else:
                QMessageBox.warning(self, "Password Change Failed", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while changing password:\n{str(e)}")

    def refresh_data(self):
        """Refresh the settings view data."""
        self.load_departments()
        self.load_user_data()
