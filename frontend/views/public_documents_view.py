from api.client import APIClient
from .base_document_view import BaseDocumentView


class PublicDocumentsView(BaseDocumentView):
    view_title = "Public Documents"
    view_description = "Publicly accessible documents available to all authenticated users"

    def __init__(self, api_client: APIClient):
        super().__init__(api_client)

    def fetch_documents(self) -> list:
        all_docs = self.api_client.get_documents()
        return [d for d in all_docs if d.get('classification') == 'public']

    def _empty_state_message(self) -> str:
        return "No public documents available yet."

    def get_action_callbacks(self, row: int) -> dict:
        callbacks = {
            'view': self.view_document,
            'download': self.download_document,
        }
        return callbacks