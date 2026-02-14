import requests
from typing import Optional, Dict, Any

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username: str, password: str) -> bool:
        """Login and store session cookie."""
        response = self.session.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        return response.status_code == 200

    def logout(self):
        """Logout and clear session."""
        self.session.post(f"{self.base_url}/auth/logout")
        self.session.cookies.clear()

    def signup(self, username: str, password: str, email: str, first_name: str, last_name: str, department_id: Optional[int] = None) -> tuple[bool, str]:
        """Register a new user."""
        data = {
            "username": username,
            "password": password,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "department_id": department_id
        }
        response = self.session.post(f"{self.base_url}/auth/register", json=data)
        if response.status_code == 200:
            return True, "Signup successful"
        else:
            return False, response.json().get("detail", "Unknown error")

    def get_departments(self) -> list:
        """Get list of departments."""
        response = self.session.get(f"{self.base_url}/auth/departments")
        if response.status_code == 200:
            return response.json()
        return []

    def create_department(self, name: str) -> tuple[bool, str]:
        """Create a new department."""
        response = self.session.post(f"{self.base_url}/admin/departments", json={"name": name})
        if response.status_code == 200:
            return True, "Department created successfully"
        return False, response.json().get("detail", "Unknown error")

    def update_department(self, dept_id: int, name: str) -> tuple[bool, str]:
        """Rename a department."""
        response = self.session.put(f"{self.base_url}/admin/departments/{dept_id}", json={"name": name})
        if response.status_code == 200:
            return True, "Department updated successfully"
        return False, response.json().get("detail", "Unknown error")

    def delete_department(self, dept_id: int) -> tuple[bool, str]:
        """Delete a department (unassigns its users)."""
        response = self.session.delete(f"{self.base_url}/admin/departments/{dept_id}")
        if response.status_code == 200:
            return True, "Department deleted successfully"
        return False, response.json().get("detail", "Unknown error")

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user info including role."""
        response = self.session.get(f"{self.base_url}/auth/me")
        if response.status_code == 200:
            user_data = response.json()
            # Ensure role is included (default to 'user' if not present)
            if 'role' not in user_data:
                user_data['role'] = 'user'
            return user_data
        return None

    def upload_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a file."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post(f"{self.base_url}/upload", files=files)
        if response.status_code == 200:
            return response.json()
        return None

    def get_documents(self) -> list:
        """Get user's accessible documents."""
        response = self.session.get(f"{self.base_url}/documents")
        if response.status_code == 200:
            return response.json()
        return []

    def get_my_documents(self) -> list:
        """Get documents owned by the current user."""
        response = self.session.get(f"{self.base_url}/documents/owned-by-me")
        if response.status_code == 200:
            return response.json()
        return []

    def get_department_documents(self) -> list:
        """Get documents from the user's department."""
        response = self.session.get(f"{self.base_url}/documents/department")
        if response.status_code == 200:
            return response.json()
        return []

    def get_shared_with_me_documents(self) -> list:
        """Get documents shared with user."""
        response = self.session.get(f"{self.base_url}/documents/shared-with-me")
        if response.status_code == 200:
            return response.json()
        return []

    def view_document(self, doc_id: int) -> Optional[bytes]:
        """View a document - returns file content."""
        try:
            response = self.session.get(f"{self.base_url}/documents/view/{doc_id}")
            if response.status_code == 200:
                return response.content
            else:
                return None
        except Exception as e:
            raise
    
    def get_document_details(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document details/metadata."""
        response = self.session.get(f"{self.base_url}/documents/{doc_id}")
        if response.status_code == 200:
            return response.json()
        return None

    def download_document(self, doc_id: int, save_path: str) -> bool:
        """Download a document."""
        response = self.session.get(f"{self.base_url}/documents/download/{doc_id}")
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False

    def update_document(self, doc_id: int, filename: str, classification: str) -> bool:
        """Update document metadata."""
        response = self.session.put(f"{self.base_url}/documents/{doc_id}", json={
            "filename": filename,
            "classification": classification
        })
        return response.status_code == 200

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document."""
        response = self.session.delete(f"{self.base_url}/documents/{doc_id}")
        return response.status_code == 200

    def share_document(self, doc_id: int, user_id: int, permission: str) -> bool:
        """Share document with user."""
        response = self.session.post(f"{self.base_url}/documents/{doc_id}/share", json={
            "user_id": user_id,
            "permission": permission
        })
        return response.status_code == 200

    def get_users(self, search: Optional[str] = None) -> list:
        """Get list of users with optional search."""
        params = {"search": search} if search else {}
        response = self.session.get(f"{self.base_url}/auth/users", params=params)
        if response.status_code == 200:
            return response.json()
        return []

    def get_document_permissions(self, doc_id: int) -> list:
        """Get list of users who have access to this document."""
        response = self.session.get(f"{self.base_url}/documents/{doc_id}/permissions")
        if response.status_code == 200:
            return response.json()
        return []

    def revoke_permission(self, doc_id: int, permission_id: int) -> bool:
        """Revoke a user's access to a document."""
        response = self.session.delete(f"{self.base_url}/documents/{doc_id}/permissions/{permission_id}")
        return response.status_code == 200

    def update_permission(self, doc_id: int, permission_id: int, permission_level: str) -> bool:
        """Update a user's permission level for a document."""
        response = self.session.put(
            f"{self.base_url}/documents/{doc_id}/permissions/{permission_id}",
            params={"permission_level": permission_level}
        )
        return response.status_code == 200

    def get_dashboard_summary(self) -> Optional[Dict[str, Any]]:
        """Get dashboard summary data."""
        response = self.session.get(f"{self.base_url}/dashboard/summary")
        if response.status_code == 200:
            return response.json()
        return None

    def log_security_event(self, activity_type: str, metadata: Optional[Dict[str, Any]] = None,
                           image_data: Optional[str] = None) -> bool:
        """Log a security event with optional camera capture image."""
        data = {
            "activity_type": activity_type,
            "metadata": metadata or {}
        }
        if image_data:
            data["image_data"] = image_data
        try:
            response = self.session.post(f"{self.base_url}/security/log", json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to log security event: {e}")
            return False
    
    def get_security_log_image(self, log_id: int) -> Optional[str]:
        """Retrieve the captured camera image for a specific security log."""
        try:
            print(f"[API] get_security_log_image: requesting /security/logs/{log_id}/image ...")
            response = self.session.get(
                f"{self.base_url}/security/logs/{log_id}/image",
                timeout=15  # Base64 images can be large, allow generous timeout
            )
            print(f"[API] get_security_log_image: status={response.status_code}, content_length={len(response.content)}")
            if response.status_code == 200:
                data = response.json()
                img = data.get("image_data")
                print(f"[API] get_security_log_image: image_data is {'None' if img is None else f'{len(img)} chars'}")
                return img
            else:
                print(f"[API] get_security_log_image: non-200 response: {response.text[:200]}")
        except Exception as e:
            print(f"[API] get_security_log_image: EXCEPTION {type(e).__name__}: {e}")
        return None
    
    def is_admin(self) -> bool:
        """Check if current user has admin role."""
        user = self.get_current_user()
        if user and isinstance(user, dict):
            return user.get('role') == 'admin'
        return False
    
    def admin_create_user(self, username: str, password: str, email: str, first_name: str, 
                         last_name: str, role: str = 'user', department_id: Optional[int] = None) -> tuple[bool, str]:
        """Admin endpoint to create a new user."""
        data = {
            "username": username,
            "password": password,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "department_id": department_id
        }
        response = self.session.post(f"{self.base_url}/auth/register", json=data)
        if response.status_code == 200:
            return True, "User created successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
    
    def update_profile(self, email: str, first_name: str, last_name: str, 
                      department_id: Optional[int] = None) -> tuple[bool, str]:
        """Update current user's profile information."""
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "department_id": department_id
        }
        response = self.session.put(f"{self.base_url}/auth/profile", json=data)
        if response.status_code == 200:
            return True, "Profile updated successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
    
    def admin_get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Admin endpoint to get specific user details."""
        response = self.session.get(f"{self.base_url}/auth/users/{user_id}")
        if response.status_code == 200:
            return response.json()
        return None
    
    def admin_update_user(self, user_id: int, email: str, first_name: str, last_name: str,
                         username: str, role: str, department_id: Optional[int] = None) -> tuple[bool, str]:
        """Admin endpoint to update any user's profile."""
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "role": role,
            "department_id": department_id
        }
        response = self.session.put(f"{self.base_url}/auth/users/{user_id}", json=data)
        if response.status_code == 200:
            return True, "User updated successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
    
    def admin_delete_user(self, user_id: int) -> tuple[bool, str]:
        """Admin endpoint to delete a user."""
        response = self.session.delete(f"{self.base_url}/auth/users/{user_id}")
        if response.status_code == 200:
            return True, "User deleted successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
    
    def admin_reset_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        """Admin endpoint to reset a user's password."""
        data = {"new_password": new_password}
        response = self.session.put(f"{self.base_url}/auth/users/{user_id}/reset-password", json=data)
        if response.status_code == 200:
            return True, "Password reset successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
    
    def get_classification_status(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Poll classification pipeline status.

        Returns:
            dict with status data on success,
            {"status": "rate_limited"} on 429 (caller should back off),
            None on network errors (caller retries next tick).
        """
        try:
            response = self.session.get(
                f"{self.base_url}/documents/{doc_id}/classification-status",
                timeout=5  # Short timeout — polling should be fast
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429:
                # Rate limited by slowapi — signal caller to back off
                return {"status": "rate_limited"}
            return None
        except Exception:
            return None  # Network hiccup, retry next tick

    def retry_classification(self, doc_id: int) -> bool:
        """Retry classification for a failed document.

        Calls POST /documents/{doc_id}/retry-classification.
        Returns True on success, raises on failure.
        Used by the retry button in the upload error dialog.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/documents/{doc_id}/retry-classification",
                timeout=10
            )
            if response.status_code == 200:
                return True
            raise Exception(f"Retry failed: {response.status_code} - {response.text}")
        except Exception:
            raise  # Let caller handle

    def change_password(self, current_password: str, new_password: str) -> tuple[bool, str]:
        """Change current user's password."""
        data = {
            "current_password": current_password,
            "new_password": new_password
        }
        response = self.session.put(f"{self.base_url}/auth/change-password", json=data)
        if response.status_code == 200:
            return True, "Password changed successfully"
        else:
            return False, response.json().get("detail", "Unknown error")
