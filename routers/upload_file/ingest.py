from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from utils.document_processer import DocumentConverter
from fastapi.responses import JSONResponse
router: APIRouter = APIRouter(tags=["Part 1 INGEST"])

@router.post("/ingest")
def ingest_document(file: UploadFile = File(...), name: str = Form(...)):
    if file.filename == '':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")
    try:
        process_pdf: DocumentConverter = DocumentConverter(file, name=name)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server Error")

    if not process_pdf.prep_pine_code_sdk():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server Error")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "File ingested successfully"})
