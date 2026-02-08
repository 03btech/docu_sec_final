from PyQt6.QtWidgets import QMessageBox
from api.client import APIClient
from widgets.enhanced_share_dialog import EnhancedShareDialog
from widgets.manage_sharing_dialog import ManageSharingDialog
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

        callbacks = {
            'view': self.view_document,
            'delete': self.delete_document,
        }

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
