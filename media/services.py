# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Media Processing Services
=========================================================
Document and image processing pipelines
"""
import io
import os
import re
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from PIL import Image as PILImage

logger = logging.getLogger('data_layer.media')


class DocumentSanitizer:
    """Sanitize documents to remove potentially dangerous content"""

    DANGEROUS_PATTERNS = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'<%',
        b'%>',
        b'<?php',
        b'<?=',
        b'eval(',
        b'exec(',
        b'system(',
    ]

    def sanitize(self, file_content: bytes, filename: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Sanitize document content.
        Returns: (sanitized_content, metadata)
        """
        metadata = {
            'original_size': len(file_content),
            'sanitized': False,
            'threats_found': [],
        }

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in file_content.lower() if isinstance(file_content, bytes) else pattern in file_content.lower().encode():
                metadata['threats_found'].append(pattern.decode('utf-8', errors='ignore'))

        if metadata['threats_found']:
            logger.warning(f"Dangerous patterns found in {filename}: {metadata['threats_found']}")
            # Remove dangerous content
            sanitized = file_content
            for pattern in self.DANGEROUS_PATTERNS:
                sanitized = sanitized.replace(pattern, b'')
                sanitized = sanitized.replace(pattern.upper(), b'')
            metadata['sanitized'] = True
            metadata['sanitized_size'] = len(sanitized)
            return sanitized, metadata

        return file_content, metadata


class ImageSanitizer:
    """Sanitize images to remove metadata and potential threats"""

    DANGEROUS_PATTERNS = [
        b'<script',
        b'<?php',
        b'<%',
    ]

    def sanitize(self, image_bytes: bytes, filename: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Sanitize image by removing EXIF and checking for embedded code.
        Returns: (sanitized_bytes, metadata)
        """
        metadata = {
            'original_size': len(image_bytes),
            'sanitized': False,
            'exif_removed': False,
            'threats_found': [],
        }

        # Check for embedded dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in image_bytes:
                metadata['threats_found'].append(pattern.decode('utf-8', errors='ignore'))

        try:
            # Open image and strip EXIF
            img = PILImage.open(io.BytesIO(image_bytes))

            # Get original format
            original_format = img.format or 'PNG'

            # Create new image without EXIF
            if img.mode in ('RGBA', 'LA', 'P'):
                # Keep alpha channel
                clean_img = PILImage.new(img.mode, img.size)
            else:
                clean_img = PILImage.new('RGB', img.size)

            clean_img.paste(img)

            # Save to bytes
            output = io.BytesIO()
            clean_img.save(output, format=original_format, quality=95)
            sanitized_bytes = output.getvalue()

            metadata['sanitized'] = True
            metadata['exif_removed'] = True
            metadata['sanitized_size'] = len(sanitized_bytes)
            metadata['format'] = original_format
            metadata['dimensions'] = img.size

            return sanitized_bytes, metadata

        except Exception as e:
            logger.error(f"Error sanitizing image {filename}: {e}")
            metadata['error'] = str(e)
            return image_bytes, metadata


class ImageCompressor:
    """Compress and convert images to WebP format"""

    DEFAULT_QUALITY = 85
    MAX_SIZE_BYTES = 1024 * 1024  # 1MB

    SIZES = {
        'thumbnail': (150, 150),
        'medium': (400, 400),
        'large': (800, 800),
        'full': None,  # Original aspect ratio
    }

    def compress(self, image_bytes: bytes, max_size: int = MAX_SIZE_BYTES,
                 min_quality: int = 85) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress image to WebP format under max_size while maintaining quality.
        """
        metadata = {
            'original_size': len(image_bytes),
            'compressed': False,
        }

        try:
            img = PILImage.open(io.BytesIO(image_bytes))
            metadata['original_dimensions'] = img.size
            metadata['original_format'] = img.format

            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA'):
                # Preserve transparency
                pass
            elif img.mode == 'P':
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            # Try compression at different quality levels
            quality = 95
            while quality >= min_quality:
                output = io.BytesIO()
                img.save(output, format='WebP', quality=quality, optimize=True)
                compressed_bytes = output.getvalue()

                if len(compressed_bytes) <= max_size or quality == min_quality:
                    metadata['compressed'] = True
                    metadata['final_quality'] = quality
                    metadata['final_size'] = len(compressed_bytes)
                    metadata['compression_ratio'] = round(len(image_bytes) / len(compressed_bytes), 2)
                    return compressed_bytes, metadata

                quality -= 5

            # Couldn't compress enough, return at min quality
            output = io.BytesIO()
            img.save(output, format='WebP', quality=min_quality, optimize=True)
            compressed_bytes = output.getvalue()

            metadata['compressed'] = True
            metadata['final_quality'] = min_quality
            metadata['final_size'] = len(compressed_bytes)
            metadata['compression_ratio'] = round(len(image_bytes) / len(compressed_bytes), 2)

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            metadata['error'] = str(e)
            return image_bytes, metadata

    def create_versions(self, image_bytes: bytes) -> Dict[str, Tuple[bytes, Dict[str, Any]]]:
        """
        Create multiple size versions of an image.
        Returns dict of {size_name: (bytes, metadata)}
        """
        versions = {}

        try:
            img = PILImage.open(io.BytesIO(image_bytes))
            original_size = img.size

            for size_name, dimensions in self.SIZES.items():
                if dimensions is None:
                    # Full size, just compress
                    compressed, meta = self.compress(image_bytes)
                    versions[size_name] = (compressed, meta)
                else:
                    # Resize and compress
                    resized = img.copy()
                    resized.thumbnail(dimensions, PILImage.Resampling.LANCZOS)

                    output = io.BytesIO()
                    if resized.mode in ('RGBA', 'LA', 'P'):
                        resized.save(output, format='WebP', quality=self.DEFAULT_QUALITY)
                    else:
                        resized.save(output, format='WebP', quality=self.DEFAULT_QUALITY)

                    resized_bytes = output.getvalue()
                    versions[size_name] = (resized_bytes, {
                        'dimensions': resized.size,
                        'size': len(resized_bytes),
                        'format': 'WebP',
                    })

            return versions

        except Exception as e:
            logger.error(f"Error creating image versions: {e}")
            return {}


class DocumentProcessor:
    """Full document processing pipeline"""

    def __init__(self):
        self.sanitizer = DocumentSanitizer()

    def process(self, file_content: bytes, filename: str,
                document_type: str = 'other') -> Dict[str, Any]:
        """
        Full document processing pipeline:
        1. Sanitize
        2. Extract text (if possible)
        3. Parse structure (for CVs)
        """
        result = {
            'success': False,
            'filename': filename,
            'document_type': document_type,
            'steps': [],
        }

        # Step 1: Sanitize
        try:
            sanitized_content, sanitize_meta = self.sanitizer.sanitize(file_content, filename)
            result['steps'].append({
                'step': 'sanitize',
                'success': True,
                'metadata': sanitize_meta
            })
            result['content'] = sanitized_content
        except Exception as e:
            result['steps'].append({
                'step': 'sanitize',
                'success': False,
                'error': str(e)
            })
            return result

        # Step 2: Extract text (basic - for full implementation use libraries like pdfplumber)
        extracted_text = ''
        try:
            # Basic text extraction for text-based files
            if filename.lower().endswith('.txt'):
                extracted_text = sanitized_content.decode('utf-8', errors='ignore')
            # For PDFs and DOCs, you'd use specialized libraries
            result['extracted_text'] = extracted_text
            result['steps'].append({
                'step': 'extract_text',
                'success': True,
                'text_length': len(extracted_text)
            })
        except Exception as e:
            result['steps'].append({
                'step': 'extract_text',
                'success': False,
                'error': str(e)
            })

        result['success'] = True
        result['final_size'] = len(sanitized_content)

        return result


class ImageProcessor:
    """Full image processing pipeline"""

    def __init__(self):
        self.sanitizer = ImageSanitizer()
        self.compressor = ImageCompressor()

    def process(self, image_bytes: bytes, filename: str,
                create_versions: bool = True) -> Dict[str, Any]:
        """
        Full image processing pipeline:
        1. Sanitize (remove EXIF, check for threats)
        2. Compress to WebP
        3. Create multiple sizes (optional)
        """
        result = {
            'success': False,
            'filename': filename,
            'steps': [],
        }

        # Step 1: Sanitize
        try:
            sanitized_bytes, sanitize_meta = self.sanitizer.sanitize(image_bytes, filename)
            result['steps'].append({
                'step': 'sanitize',
                'success': True,
                'metadata': sanitize_meta
            })
        except Exception as e:
            result['steps'].append({
                'step': 'sanitize',
                'success': False,
                'error': str(e)
            })
            return result

        # Step 2: Compress
        try:
            compressed_bytes, compress_meta = self.compressor.compress(sanitized_bytes)
            result['steps'].append({
                'step': 'compress',
                'success': True,
                'metadata': compress_meta
            })
            result['content'] = compressed_bytes
        except Exception as e:
            result['steps'].append({
                'step': 'compress',
                'success': False,
                'error': str(e)
            })
            result['content'] = sanitized_bytes  # Fall back to sanitized

        # Step 3: Create versions
        if create_versions:
            try:
                versions = self.compressor.create_versions(sanitized_bytes)
                result['versions'] = {k: v[1] for k, v in versions.items()}  # Metadata only
                result['version_bytes'] = {k: v[0] for k, v in versions.items()}  # Actual bytes
                result['steps'].append({
                    'step': 'create_versions',
                    'success': True,
                    'versions': list(versions.keys())
                })
            except Exception as e:
                result['steps'].append({
                    'step': 'create_versions',
                    'success': False,
                    'error': str(e)
                })

        result['success'] = True
        return result

