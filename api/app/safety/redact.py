import re
import base64
from io import BytesIO
from PIL import Image

PHONE_REGEX = re.compile(r'\b(01[016789])[-.\s]?(\d{3,4})[-.\s]?(\d{4})\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
RRN_REGEX = re.compile(r'\b\d{6}[-.\s]?[1-4]\d{6}\b') # Resident registration number

def redact_text(text: str) -> str:
    """Mask phone numbers, emails, and RRNs in a given text string."""
    if not text:
        return text
    
    # Redact phone numbers -> 010-****-1234
    text = PHONE_REGEX.sub(r'\1-****-\3', text)
    
    # Redact emails -> e***@domain.com
    def mask_email(m):
        email = m.group(0)
        parts = email.split('@')
        if len(parts) == 2:
            name, domain = parts
            masked_name = name[0] + '*' * (len(name) - 1) if len(name) > 1 else '*'
            return f'{masked_name}@{domain}'
        return email
    text = EMAIL_REGEX.sub(mask_email, text)
    
    # Redact RRN -> 950101-*******
    text = RRN_REGEX.sub(lambda m: m.group(0)[:7] + '*******', text)
    
    return text

def redact_exif(base64_image: str) -> str:
    """Strip EXIF metadata from a base64-encoded image."""
    try:
        img_bytes = base64.b64decode(base64_image)
        img = Image.open(BytesIO(img_bytes))
        
        # Pillow does not save exif by default unless requested.
        # This completely strips exif, GPS coords, camera info, etc.
        out_buf = BytesIO()
        fmt = img.format or 'JPEG'
        
        if fmt == 'JPEG' and img.mode in ('RGBA', 'LA'):
            img = img.convert('RGB')
            
        img.save(out_buf, format=fmt)
        return base64.b64encode(out_buf.getvalue()).decode('utf-8')
    except Exception:
        # Fallback to the original base64 if processing fails
        return base64_image

def redact_image(base64_image: str) -> str:
    """Redact PII in image (strips EXIF metadata containing GPS/location coords)."""
    return redact_exif(base64_image)
