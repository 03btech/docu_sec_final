from api.client import APIClient
from .base_document_view import BaseDocumentView


class DepartmentDocumentsView(BaseDocumentView):
    view_title = "Department Documents"
    view_description = "Documents shared within your department"

    def __init__(self, api_client: APIClient):
        super().__init__(api_client)

    def fetch_documents(self) -> list:
        return self.api_client.get_department_documents()

    def _empty_state_message(self) -> str:
        return "No department documents available yet."

    def get_action_callbacks(self, row: int) -> dict:
        doc = self.documents[row]
        classification = doc.get('classification', 'unclassified').lower()

        callbacks = {'view': self.view_document}
        if classification != 'confidential':
            callbacks['download'] = self.download_document
        return callbacks