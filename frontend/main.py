import sys
from PyQt6.QtWidgets import QApplication
from api.client import APIClient
from views.login_window import LoginWindow
from views.main_window import MainWindow

# Keep a strong reference to the main window globally
main_window = None

def main():
    print("Starting application...")
    app = QApplication(sys.argv)
    
    # Load theme
    try:
        with open('assets/style.qss', 'r') as f:
            app.setStyleSheet(f.read())
        print("Theme loaded successfully.")
    except FileNotFoundError:
        print("Warning: style.qss not found, using default theme")

    # API Client
    api_client = APIClient()
    print("API client initialized.")

    # Show login window
    login_window = LoginWindow(api_client)
    login_window.show()
    print("Login window displayed.")

    def on_login_successful():
        global main_window
        print("Login successful, creating main window")
        # Store globally to prevent garbage collection
        main_window = MainWindow(api_client)
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
        login_window.close()

    login_window.login_successful.connect(on_login_successful)
    
    print("Entering application event loop.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
