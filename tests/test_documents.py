from document.request import DocumentCreateRequest, DocumentUpdateRequest
from document.response import DocumentListResponse, DocumentResponse


def test_document_create_request_accepts_editable_metadata():
    request = DocumentCreateRequest(
        title="Company Handbook",
        description="Internal policies",
    )

    assert request.model_dump() == {
        "title": "Company Handbook",
        "description": "Internal policies",
    }


def test_document_update_request_allows_partial_updates():
    request = DocumentUpdateRequest(title="Updated Handbook")

    assert request.model_dump(exclude_unset=True) == {"title": "Updated Handbook"}


def test_document_list_response_has_pagination_contract():
    response = DocumentListResponse(
        items=[],
        total=0,
        page=1,
        page_size=20,
        pages=0,
    )

    assert response.items == []
    assert response.total == 0
    assert "storage_key" not in DocumentResponse.model_fields
