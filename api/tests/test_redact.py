import base64
from io import BytesIO
from PIL import Image
from api.app.safety.redact import redact_text, redact_exif

def test_redact_text_phone():
    text = "제 번호는 010-1234-5678 입니다."
    redacted = redact_text(text)
    assert "010-****-5678" in redacted
    assert "1234" not in redacted

def test_redact_text_email():
    text = "이메일은 test_user@example.com 입니다."
    redacted = redact_text(text)
    assert "t********@example.com" in redacted
    assert "test_user" not in redacted

def test_redact_text_rrn():
    text = "주민등록번호는 950101-1234567 입니다."
    redacted = redact_text(text)
    assert "950101-*******" in redacted
    assert "1234567" not in redacted

def test_redact_exif():
    # 1. Create a dummy image with EXIF metadata
    img = Image.new("RGB", (100, 100), color="red")
    
    # Save image to base64
    buf = BytesIO()
    # Pillow allows writing exif on save
    exif_data = Image.Exif()
    exif_data[0x0112] = 1 # Orientation
    img.save(buf, format="JPEG", exif=exif_data)
    
    b64_original = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    # 2. Assert original image has EXIF
    img_read = Image.open(BytesIO(buf.getvalue()))
    assert img_read.getexif() is not None
    assert 0x0112 in img_read.getexif()
    
    # 3. Redact
    b64_redacted = redact_exif(b64_original)
    
    # 4. Assert redacted image does not have EXIF
    img_redacted = Image.open(BytesIO(base64.b64decode(b64_redacted)))
    # Exif should be stripped / empty
    assert not img_redacted.getexif()
