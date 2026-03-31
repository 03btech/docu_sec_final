from PyQt6.QtWidgets import QMessageBox
from api.client import APIClient
from widgets.enhanced_share_dialog import EnhancedShareDialog
from widgets.manage_sharing_dialog import ManageSharingDialog
from widgets.classification_dialog import ClassificationDialog
from .base_document_view import BaseDocumentView


class MyDocumentsView(BaseDocumentView):
    view_title = "My Documents"
    view_description = "Documents you own and have uploaded to the system"

    def __init__(self, api_client: APIClient):
        super().__init__(api_client)

    def fetch_documents(self) -> list:
        return self.api_client.get_my_documents()

    def _empty_state_message(self) -> str:
        return "You haven't uploaded any documents yet.\nGo to 'Upload Document' to get started."

    def get_action_callbacks(self, row: int) -> dict:
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()
        classification_status = doc.get('classification_status', 'completed')

        callbacks = {
            'view': self.view_document,
            'delete': self.delete_document,
            'change_classification': self.change_classification,
        }

        # Show retry for failed classifications
        if classification_status == 'failed':
            callbacks['retry'] = self.retry_classification

        if classification == 'confidential':
            callbacks['share'] = self.share_document
            callbacks['manage_sharing'] = self.manage_sharing

        if classification != 'confidential':
            callbacks['download'] = self.download_document

        return callbacks

    def share_document(self, row):
        """Open share dialog for confidential documents."""
        doc = self.documents[row]
        if doc.get('classification', '').lower() != 'confidential':
            QMessageBox.warning(self, "Not Allowed",
                                "Only confidential documents can be shared with other users.")
            return
        dialog = EnhancedShareDialog(doc, self.api_client, self)
        dialog.exec()

    def manage_sharing(self, row):
        """Open manage sharing dialog for confidential documents."""
        doc = self.documents[row]
        dialog = ManageSharingDialog(doc, self.api_client, self)
        dialog.exec()

    def retry_classification(self, row):
        """Retry classification for a failed document."""
        doc = self.documents[row]
        confirm = QMessageBox.question(
            self, "Retry Classification?",
            f"Retry AI classification for '{doc.get('filename')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.retry_classification(doc['id'])
                QMessageBox.information(
                    self, "Retrying",
                    "Classification has been requeued. Refresh to see the updated status."
                )
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "Retry Failed", f"Could not retry classification: {e}")

    def change_classification(self, row):
        """Open dialog to manually change a document's classification and department tags."""
        doc = self.documents[row]
        dialog = ClassificationDialog(doc, self.api_client, self)
        if dialog.exec():
            new_classification = dialog.selected_classification
            new_departments = dialog.selected_departments
            
            # Check if either classification or departments changed
            current_classification = doc.get('classification')
            current_departments = [d.get('department_id') for d in doc.get('departments', [])]
            
            if new_classification != current_classification or set(new_departments) != set(current_departments):
                try:
                    success = self.api_client.update_document(
                        doc['id'], doc.get('filename', ''), new_classification, new_departments
                    )
                    if success:
                        QMessageBox.information(
                            self, "Metadata Updated",
                            "Document classification and department tags updated successfully."
                        )
                        self.load_documents()
                    else:
                        QMessageBox.critical(
                            self, "Update Failed",
                            "Could not update document metadata on the server."
                        )
                except Exception as e:
                    QMessageBox.critical(
                        self, "Update Failed",
                        f"Could not update document metadata: {e}"
                    )
