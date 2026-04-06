import pymupdf
from fastapi import UploadFile

class TextExtractor:
    @staticmethod
    def extract(file: UploadFile) -> tuple[str, dict]:
        """Returns (text, extra_meta)"""
        extension = file.filename.split(".")[-1].lower()

        if extension == "pdf":
            return TextExtractor._from_pdf(file)
        elif extension == "txt":
            return TextExtractor._from_txt(file)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    @staticmethod
    def _from_pdf(file: UploadFile) -> tuple[str, dict]:
        pdf_bytes = file.file.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text = "".join([page.get_text() for page in doc]).replace("\n", " ")
        meta = {
            "author": doc.metadata.get("author", ""),
            "title": doc.metadata.get("title", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "page_count": doc.page_count,
        }
        return text, meta

    @staticmethod
    def _from_txt(file: UploadFile) -> tuple[str, dict]:
        text = file.file.read().decode("utf-8").replace("\n", " ")
        meta = {"author": "", "title": "", "page_count": 1}
        return text, meta