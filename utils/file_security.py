"""
File Upload Security Utilities
Provides comprehensive file upload validation and security checks
"""
import os
import hashlib
import shutil
from pathlib import Path
from fastapi import HTTPException, status, UploadFile
from typing import Dict, List, Set, Tuple
import logging
import tempfile
from datetime import datetime

# Import PIL with fallback
try:
    from PIL import Image
except ImportError:
    Image = None
    logging.warning("PIL (Pillow) not available - image validation will be limited")

# Import magic with fallback
try:
    import magic
except ImportError:
    magic = None
    logging.warning("python-magic not available - MIME type detection will use fallback method")

logger = logging.getLogger(__name__)

class FileSecurityValidator:
    """Comprehensive file upload security validator"""

    # Allowed MIME types for images
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp'
    }

    # Maximum file sizes (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB for images

    # Dangerous file signatures (magic numbers)
    DANGEROUS_SIGNATURES = {
        b'\x4D\x5A': 'PE executable (Windows)',
        b'\x7F\x45\x4C\x46': 'ELF executable (Linux/Unix)',
        b'\xCA\xFE\xBA\xBE': 'Java class file',
        b'\xFE\xED\xFA': 'Mach-O executable (macOS)',
        b'\x89\x50\x4E\x47': 'PNG (but check for malicious content)',
        b'\xFF\xD8\xFF': 'JPEG (but check for malicious content)',
    }

    # File extensions that should be blocked
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.sh', '.py', '.pl', '.php', '.asp', '.jsp', '.war', '.ear',
        '.dll', '.so', '.dylib', '.ocx', '.sys', '.drv',
        '.ps1', '.vbe', '.wsf', '.wsh', '.msc', '.msi', '.msp',
        '.reg', '.lnk', '.url', '.chm', '.hlp', '.inf'
    }

    def __init__(self):
        """Initialize file security validator"""
        try:
            import magic
            self.magic = magic.Magic(mime=True)
        except ImportError as e:
            logger.warning(f"python-magic not installed: {e}")
            self.magic = None
        except Exception as e:
            logger.warning(f"Could not initialize python-magic: {e}")
            self.magic = None

    def validate_file_upload(self, file: UploadFile, allowed_types: Set[str] = None):
        """
        Comprehensive file upload validation

        Args:
            file: The uploaded file
            allowed_types: Set of allowed MIME types

        Returns:
            Dict with validation results

        Raises:
            HTTPException: If validation fails
        """
        if allowed_types is None:
            allowed_types = self.ALLOWED_IMAGE_TYPES

        # Get file extension
        file_extension = Path(file.filename).suffix.lower()

        # Check file extension
        if file_extension in self.BLOCKED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{file_extension}' is not allowed"
            )

        # Check filename length
        if len(file.filename) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is too long (maximum 255 characters)"
            )

        # Validate filename characters (prevent path traversal)
        if any(char in file.filename for char in ['/', '\\', '..', '\0']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in filename"
            )

        # Read file content for analysis
        file_content = file.file.read()
        file_size = len(file_content)

        # Check file size
        if file_size > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({self.MAX_IMAGE_SIZE} bytes)"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file not allowed"
            )

        # Detect MIME type
        detected_mime = None
        if self.magic:
            try:
                detected_mime = self.magic.from_buffer(file_content)
            except Exception as e:
                logger.warning(f"MIME type detection failed: {e}")

        # Fallback MIME detection using file signature
        if not detected_mime:
            detected_mime = self._detect_mime_from_signature(file_content)

        # Validate MIME type
        if detected_mime not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{detected_mime}' is not allowed. Allowed types: {', '.join(allowed_types)}"
            )

        # Check for malicious file signatures
        self._check_malicious_signatures(file_content)

        # Validate image content (for image files)
        if detected_mime.startswith('image/'):
            self._validate_image_content(file_content, detected_mime)

        # Generate file hash for integrity checking
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Reset file pointer for further processing
        file.file.seek(0)

        return {
            'filename': file.filename,
            'file_size': file_size,
            'mime_type': detected_mime,
            'file_hash': file_hash,
            'extension': file_extension,
            'is_valid': True
        }

    def _detect_mime_from_signature(self, content: bytes) -> str:
        """Detect MIME type from file signature (magic numbers)"""
        if len(content) < 8:
            return 'application/octet-stream'

        # Check for common image signatures
        if content.startswith(b'\xFF\xD8\xFF'):
            return 'image/jpeg'
        elif content.startswith(b'\x89\x50\x4E\x47'):
            return 'image/png'
        elif content.startswith(b'\x47\x49\x46'):
            return 'image/gif'
        elif content.startswith(b'\x52\x49\x46\x46') and len(content) >= 12 and content[8:12] == b'\x57\x45\x42\x50':
            return 'image/webp'

        return 'application/octet-stream'

    def _check_malicious_signatures(self, content: bytes):
        """Check for malicious file signatures"""
        for signature, description in self.DANGEROUS_SIGNATURES.items():
            if content.startswith(signature):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File appears to be a {description}. This file type is not allowed."
                )

    def _validate_image_content(self, content: bytes, mime_type: str):
        """Validate image content for corruption and malicious data"""
        try:
            # Try to open image with PIL to check for corruption
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()

                with Image.open(tmp_file.name) as img:
                    # Check image dimensions (prevent decompression bombs)
                    width, height = img.size
                    if width > 5000 or height > 5000:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Image dimensions too large: {width}x{height}. Maximum allowed: 5000x5000 pixels"
                        )

                    # Check if image has reasonable file size for its dimensions
                    expected_size = (width * height * 3) / 1024  # Rough estimate in KB
                    actual_size_kb = len(content) / 1024

                    if actual_size_kb > expected_size * 10:  # 10x larger than expected
                        logger.warning(f"Suspiciously large image file: {actual_size_kb}KB for {width}x{height} image")

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted image file"
            )

    def generate_secure_filename(self, original_filename: str, user_id: str) -> str:
        """Generate a secure filename with user ID prefix"""
        import uuid

        file_extension = Path(original_filename).suffix.lower()

        # Ensure extension is safe
        if file_extension in self.BLOCKED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{file_extension}' is not allowed"
            )

        # Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        secure_filename = f"{user_id}_{unique_id}{file_extension}"

        return secure_filename

def validate_profile_image(file: UploadFile) -> Dict:
    """Validate profile image upload"""
    validator = FileSecurityValidator()
    return validator.validate_file_upload(file, FileSecurityValidator.ALLOWED_IMAGE_TYPES)

def validate_secure_filename(original_filename: str, user_id: str) -> str:
    """Generate secure filename for uploads"""
    validator = FileSecurityValidator()
    return validator.generate_secure_filename(original_filename, user_id)

def optimize_image(image_path: Path, max_size: tuple = (800, 800), quality: int = 85) -> Path:
    """
    Optimize image by resizing and compressing

    Args:
        image_path: Path to the image file
        max_size: Maximum dimensions (width, height)
        quality: JPEG quality (1-100)

    Returns:
        Path to optimized image (same as input if optimization not needed)
    """
    try:
        if Image is None:
            logger.warning("PIL not available - skipping image optimization")
            return image_path

        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Calculate new dimensions maintaining aspect ratio
            original_width, original_height = img.size
            max_width, max_height = max_size

            if original_width <= max_width and original_height <= max_height:
                logger.info(f"Image {image_path.name} already within size limits")
                return image_path

            # Calculate scaling factor
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_factor = min(width_ratio, height_ratio)

            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)

            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image (overwrite original)
            if image_path.suffix.lower() in ['.jpg', '.jpeg']:
                resized_img.save(image_path, 'JPEG', quality=quality, optimize=True)
            else:
                resized_img.save(image_path, 'PNG', optimize=True)

            logger.info(f"Optimized image {image_path.name}: {original_width}x{original_height} -> {new_width}x{new_height}")
            return image_path

    except Exception as e:
        logger.error(f"Failed to optimize image {image_path}: {e}")
        return image_path

def cleanup_failed_uploads(upload_dir: Path, max_age_hours: int = 24):
    """
    Clean up temporary or failed upload files

    Args:
        upload_dir: Directory to clean up
        max_age_hours: Maximum age of files to keep (hours)
    """
    try:
        if not upload_dir.exists():
            return

        current_time = datetime.now()
        cleaned_count = 0

        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                # Check file age
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() > (max_age_hours * 3600):
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up old upload file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to clean up file {file_path}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old upload files from {upload_dir}")

    except Exception as e:
        logger.error(f"Failed to cleanup upload directory {upload_dir}: {e}")

# Global validator instance
file_validator = FileSecurityValidator()
