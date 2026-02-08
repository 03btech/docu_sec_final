from api.client import APIClient
from .base_document_view import BaseDocumentView


class SharedDocumentsView(BaseDocumentView):
    view_title = "Shared with Me"
    view_description = "Documents that other users have shared with you"

    def __init__(self, api_client: APIClient):
        super().__init__(api_client)

    def fetch_documents(self) -> list:
        return self.api_client.get_shared_with_me_documents()

    def _empty_state_message(self) -> str:
        return "No documents have been shared with you yet."

    def get_action_callbacks(self, row: int) -> dict:
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()

        callbacks = {'view': self.view_document}
        if classification != 'confidential':
            callbacks['download'] = self.download_document
        return callbacks