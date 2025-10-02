"""
Camera utilities for checking camera availability.
"""
import cv2


def check_camera_available(camera_index=0) -> tuple[bool, str]:
    """
    Check if a camera is available and accessible.
    
    Returns:
        tuple: (is_available: bool, message: str)
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return False, "No camera detected. Please connect a camera to proceed."
        
        # Try to read a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return False, "Camera detected but unable to read frames."
        
        return True, "Camera available and operational."
        
    except Exception as e:
        return False, f"Camera check failed: {str(e)}"


def list_available_cameras(max_check=5) -> list[int]:
    """
    List all available camera indices.
    
    Args:
        max_check: Maximum number of camera indices to check
        
    Returns:
        list: List of available camera indices
    """
    available = []
    
    for i in range(max_check):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
            cap.release()
        except:
            pass
    
    return available
