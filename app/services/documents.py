"""
Document upload and management service.
"""

import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import shutil

from app.models.database import UserDocument
from app.models.schemas import DocumentCreate, DocumentType

class DocumentService:
    """Service for handling document uploads and management."""
    
    def __init__(self, upload_base_path: str = "uploads"):
        self.upload_base_path = upload_base_path
        os.makedirs(upload_base_path, exist_ok=True)
    
    def save_document(
        self,
        db: Session,
        user_id: int,
        document_data: DocumentCreate,
        file_content: bytes,
        original_filename: str,
        mime_type: str = None
    ) -> UserDocument:
        """Save an uploaded document."""
        
        # Generate unique filename
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create user-specific directory
        user_upload_dir = os.path.join(self.upload_base_path, str(user_id), document_data.document_type.value)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(user_upload_dir, unique_filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        db_document = UserDocument(
            user_id=user_id,
            document_type=document_data.document_type.value,
            original_filename=original_filename,
            stored_filename=unique_filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=mime_type,
            upload_date=datetime.utcnow()
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return db_document
    
    def get_user_documents(self, db: Session, user_id: int, document_type: Optional[str] = None) -> list[UserDocument]:
        """Get all documents for a user, optionally filtered by type."""
        query = db.query(UserDocument).filter(UserDocument.user_id == user_id)
        
        if document_type:
            query = query.filter(UserDocument.document_type == document_type)
        
        return query.order_by(UserDocument.upload_date.desc()).all()
    
    def get_document_by_id(self, db: Session, document_id: int, user_id: Optional[int] = None) -> Optional[UserDocument]:
        """Get a document by ID, optionally verifying user ownership."""
        query = db.query(UserDocument).filter(UserDocument.id == document_id)
        
        if user_id:
            query = query.filter(UserDocument.user_id == user_id)
        
        return query.first()
    
    def delete_document(self, db: Session, document_id: int, user_id: int) -> bool:
        """Delete a document and its file."""
        document = self.get_document_by_id(db, document_id, user_id)
        
        if not document:
            return False
        
        # Delete file if it exists
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except OSError:
                # File might be locked or doesn't exist
                pass
        
        # Delete database record
        db.delete(document)
        db.commit()
        
        return True
    
    def update_document_processing_status(
        self,
        db: Session,
        document_id: int,
        status: str,
        error_message: Optional[str] = None,
        extracted_data: Optional[str] = None
    ) -> Optional[UserDocument]:
        """Update document processing status."""
        document = db.query(UserDocument).filter(UserDocument.id == document_id).first()
        
        if not document:
            return None
        
        document.processing_status = status
        
        if status == "completed":
            document.is_processed = True
            document.processed_date = datetime.utcnow()
            if extracted_data:
                document.extracted_data = extracted_data
        elif status == "failed":
            document.processing_error = error_message
        
        db.commit()
        db.refresh(document)
        
        return document
    
    def get_document_file_path(self, document: UserDocument) -> Optional[str]:
        """Get the file path for a document if it exists."""
        if os.path.exists(document.file_path):
            return document.file_path
        return None
    
    def get_document_stats(self, db: Session, user_id: int) -> dict:
        """Get document statistics for a user."""
        documents = self.get_user_documents(db, user_id)
        
        stats = {
            "total_documents": len(documents),
            "processed_documents": len([d for d in documents if d.is_processed]),
            "by_type": {},
            "processing_status": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
        }
        
        for doc in documents:
            # Count by type
            doc_type = doc.document_type
            if doc_type not in stats["by_type"]:
                stats["by_type"][doc_type] = 0
            stats["by_type"][doc_type] += 1
            
            # Count by processing status
            status = doc.processing_status
            if status in stats["processing_status"]:
                stats["processing_status"][status] += 1
        
        return stats