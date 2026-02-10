"""
Text extraction utilities for various file formats
Supports: PDF, DOCX, TXT, MD
"""

import io
import hashlib
from typing import Dict, List, Tuple
import filetype
from PyPDF2 import PdfReader
from docx import Document


class TextExtractor:
    """Extract text from uploaded files with provenance tracking"""
    
    # Allowed file types (MIME types)
    ALLOWED_TYPES = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'text/markdown': '.md',
    }
    
    # Max file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    @staticmethod
    def validate_file(file_data: bytes, filename: str) -> Tuple[bool, str, str]:
        """
        Validate file type and size using magic bytes
        
        Args:
            file_data: File contents
            filename: Original filename
        
        Returns:
            (is_valid, mime_type, error_message)
        """
        # Check size
        if len(file_data) > TextExtractor.MAX_FILE_SIZE:
            return False, '', f'File size exceeds {TextExtractor.MAX_FILE_SIZE // (1024*1024)}MB limit'
        
        # Detect MIME type using magic bytes
        kind = filetype.guess(file_data)
        
        if kind is None:
            # Fall back to text/plain or text/markdown based on extension
            if filename.endswith('.txt'):
                mime_type = 'text/plain'
            elif filename.endswith('.md'):
                mime_type = 'text/markdown'
            else:
                return False, '', 'Unknown file type'
        else:
            mime_type = kind.mime
        
        # Check if allowed
        if mime_type not in TextExtractor.ALLOWED_TYPES:
            return False, mime_type, f'File type {mime_type} not allowed'
        
        return True, mime_type, ''
    
    @staticmethod
    def extract_from_pdf(file_data: bytes) -> Dict:
        """
        Extract text from PDF with page-level provenance
        
        Returns:
            {
                'text': str,  # Full text
                'pages': List[Dict],  # Per-page data
                'page_count': int,
                'word_count': int,
                'is_scanned': bool,  # True if no text layer detected
                'sha256': str
            }
        """
        try:
            pdf_reader = PdfReader(io.BytesIO(file_data))
            pages = []
            full_text = []
            total_words = 0
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                word_count = len(text.split())
                total_words += word_count
                
                pages.append({
                    'page_num': page_num,
                    'text': text,
                    'word_count': word_count,
                    'char_start': len(''.join(full_text)),
                    'char_end': len(''.join(full_text)) + len(text)
                })
                full_text.append(text)
            
            combined_text = '\n\n'.join(full_text)
            
            # Detect scanned PDF (very low word count suggests no text layer)
            is_scanned = total_words < 50 and len(pdf_reader.pages) > 1
            
            return {
                'text': combined_text,
                'pages': pages,
                'page_count': len(pdf_reader.pages),
                'word_count': total_words,
                'is_scanned': is_scanned,
                'sha256': hashlib.sha256(file_data).hexdigest(),
                'extraction_method': 'pypdf2'
            }
        
        except Exception as e:
            raise Exception(f'PDF extraction failed: {str(e)}')
    
    @staticmethod
    def extract_from_docx(file_data: bytes) -> Dict:
        """
        Extract text from DOCX with paragraph-level provenance
        
        Returns:
            {
                'text': str,
                'paragraphs': List[Dict],
                'paragraph_count': int,
                'word_count': int,
                'sha256': str
            }
        """
        try:
            doc = Document(io.BytesIO(file_data))
            paragraphs = []
            full_text = []
            total_words = 0
            
            for para_num, para in enumerate(doc.paragraphs, start=1):
                text = para.text.strip()
                if not text:
                    continue
                
                word_count = len(text.split())
                total_words += word_count
                
                paragraphs.append({
                    'paragraph_num': para_num,
                    'text': text,
                    'word_count': word_count,
                    'char_start': len('\n\n'.join(full_text)),
                    'char_end': len('\n\n'.join(full_text)) + len(text)
                })
                full_text.append(text)
            
            combined_text = '\n\n'.join(full_text)
            
            return {
                'text': combined_text,
                'paragraphs': paragraphs,
                'paragraph_count': len(paragraphs),
                'word_count': total_words,
                'sha256': hashlib.sha256(file_data).hexdigest(),
                'extraction_method': 'python-docx'
            }
        
        except Exception as e:
            raise Exception(f'DOCX extraction failed: {str(e)}')
    
    @staticmethod
    def extract_from_text(file_data: bytes) -> Dict:
        """
        Extract text from plain text or markdown files
        
        Returns:
            {
                'text': str,
                'word_count': int,
                'line_count': int,
                'sha256': str
            }
        """
        try:
            text = file_data.decode('utf-8')
            lines = text.split('\n')
            words = text.split()
            
            return {
                'text': text,
                'word_count': len(words),
                'line_count': len(lines),
                'sha256': hashlib.sha256(file_data).hexdigest(),
                'extraction_method': 'plain_text'
            }
        
        except UnicodeDecodeError:
            raise Exception('Text file encoding not supported (must be UTF-8)')
        except Exception as e:
            raise Exception(f'Text extraction failed: {str(e)}')
    
    @staticmethod
    def extract(file_data: bytes, mime_type: str) -> Dict:
        """
        Extract text based on MIME type
        
        Args:
            file_data: File contents
            mime_type: MIME type
        
        Returns:
            Extraction result dictionary
        
        Raises:
            Exception if extraction fails
        """
        if mime_type == 'application/pdf':
            return TextExtractor.extract_from_pdf(file_data)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return TextExtractor.extract_from_docx(file_data)
        elif mime_type in ['text/plain', 'text/markdown']:
            return TextExtractor.extract_from_text(file_data)
        else:
            raise Exception(f'Unsupported MIME type: {mime_type}')
