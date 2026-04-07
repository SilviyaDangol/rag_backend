from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse

from utils.chunker import ChunkingStrategy
from utils.document_processer import DocumentConverter
from utils.redis_client import set_active_ingest

router: APIRouter = APIRouter(tags=["Part 1 INGEST"])


@router.post("/ingest")
def ingest_document(
    file: UploadFile = File(...),
    chunking_strategy: Annotated[
        ChunkingStrategy,
        Form(
            description=(
                "**fixed**: sliding character windows with overlap. "
                "**sentence**: merge whole sentences up to the chunk size (long sentences are split)."
            ),
        ),
    ] = ChunkingStrategy.fixed,
):
    if file.filename == '':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")
    try:
        process_pdf: DocumentConverter = DocumentConverter(
            file,
            name="default",
            chunking_strategy=chunking_strategy.value,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server Error")

    if not process_pdf.prep_pine_code_sdk():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server Error")
    set_active_ingest(None, process_pdf.ingest_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "File ingested successfully",
            "ingest_id": process_pdf.ingest_id,
        },
    )
