"""
TinyPNG + Pillow - Universal Image Compression Utility
=======================================================

Istalgan Django loyihada ishlatish mumkin.

Foydalanish:
-----------
from main.image_compressor import compress_image, compress_uploaded_image

# 1. Fayl yo'li bilan
result = compress_image("path/to/image.jpg", api_key="YOUR_TINYPNG_API_KEY")

# 2. Django ImageField bilan (model.save() da)
class MyModel(models.Model):
    image = models.ImageField(upload_to='images/')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            from main.image_compressor import compress_uploaded_image
            compress_uploaded_image(self.image, api_key="YOUR_API_KEY")
"""

import os
import tinify
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


# =====================================================
# 🔑 TINYPNG API KALITLARI - Limit tugasa keyingisiga o'tadi
# =====================================================
# https://tinypng.com/developers dan oling (har biri 500 ta/oy bepul)
TINYPNG_API_KEYS = [
    "68KzZybfDpsK3HYCnpmn5wxfxwnPTLLT",  # 1-kalit (asosiy)
    "S0cMWS3mtQCjfqVzPvcHQbZ88TBQ4Jlm",           # 2-kalit (zaxira)
    # "YOUR_THIRD_API_KEY_HERE",          # 3-kalit (qo'shimcha)
]
# =====================================================

# Hozirgi ishlatilayotgan kalit indeksi
_current_key_index = 0


def _get_working_key():
    """Ishlaydigan API kalitni topish"""
    global _current_key_index
    
    if _current_key_index < len(TINYPNG_API_KEYS):
        return TINYPNG_API_KEYS[_current_key_index]
    return None


def _try_next_key():
    """Keyingi kalitga o'tish"""
    global _current_key_index
    _current_key_index += 1
    
    if _current_key_index < len(TINYPNG_API_KEYS):
        print(f"🔄 TinyPNG: Keyingi kalitga o'tildi ({_current_key_index + 1}/{len(TINYPNG_API_KEYS)})")
        return True
    return False


def _compress_with_tinypng(input_path, temp_path):
    """TinyPNG bilan compress qilish - kalitlar orasida fallback"""
    global _current_key_index
    
    while _current_key_index < len(TINYPNG_API_KEYS):
        key = TINYPNG_API_KEYS[_current_key_index]
        
        try:
            tinify.key = key
            source = tinify.from_file(input_path)
            source.to_file(temp_path)
            return True, None
            
        except tinify.AccountError as e:
            error_msg = str(e)
            # Limit tugagan yoki kalit noto'g'ri
            if "limit" in error_msg.lower() or "exceeded" in error_msg.lower():
                print(f"⚠️ TinyPNG kalit #{_current_key_index + 1} limiti tugadi")
                if not _try_next_key():
                    return False, "❌ Barcha API kalitlar limiti tugagan"
            else:
                return False, f"❌ API kalit xato: {error_msg}"
                
        except tinify.ClientError as e:
            return False, f"❌ Fayl formati xato: {str(e)}"
            
        except Exception as e:
            return False, f"❌ TinyPNG xatolik: {str(e)}"
    
    return False, "❌ Ishlaydigan API kalit topilmadi"


def compress_image(
    input_path: str,
    output_path: str = None,
    jpeg_quality: int = 90,
    use_pillow: bool = True
) -> dict:
    """
    Rasmni TinyPNG + Pillow bilan compress qiladi.
    Agar bitta API kalit limiti tugasa, keyingisiga o'tadi.
    
    Args:
        input_path: Kirish rasm yo'li
        output_path: Chiqish rasm yo'li (None bo'lsa, original ustiga yozadi)
        jpeg_quality: JPEG sifati (1-100), default 90
        use_pillow: TinyPNG dan keyin Pillow ham ishlatish
    
    Returns:
        dict: {
            'success': bool,
            'original_size': int,
            'compressed_size': int,
            'saved_percent': float,
            'output_path': str,
            'message': str
        }
    """
    if not os.path.exists(input_path):
        return {
            'success': False,
            'message': f"Fayl topilmadi: {input_path}"
        }
    
    # Output yo'li
    if output_path is None:
        output_path = input_path
    
    original_size = os.path.getsize(input_path)
    temp_path = input_path + ".temp"
    
    # 1-BOSQICH: TinyPNG (fallback bilan)
    success, error = _compress_with_tinypng(input_path, temp_path)
    if not success:
        return {'success': False, 'message': error}
    
    try:
        if use_pillow:
            # 2-BOSQICH: Pillow bilan qo'shimcha optimizatsiya
            img = Image.open(temp_path)
            ext = os.path.splitext(input_path)[1].lower()
            
            if ext in ['.jpg', '.jpeg']:
                img = img.convert("RGB")
                img.save(output_path, format="JPEG", quality=jpeg_quality, optimize=True, progressive=True)
            elif ext == '.png':
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
                img.save(output_path, format="PNG", optimize=True)
            else:
                img.save(output_path, optimize=True)
            
            # Temp ni o'chirish
            if os.path.exists(temp_path):
                os.remove(temp_path)
        else:
            # Faqat TinyPNG - temp ni output ga ko'chirish
            import shutil
            shutil.move(temp_path, output_path)
        
        compressed_size = os.path.getsize(output_path)
        saved_percent = round((1 - compressed_size / original_size) * 100, 2)
        
        return {
            'success': True,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'saved_percent': saved_percent,
            'output_path': output_path,
            'message': f"✅ {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({saved_percent}% tejaldi)"
        }
        
    except Exception as e:
        # Temp faylni tozalash
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return {
            'success': False,
            'message': f"❌ Pillow xatolik: {str(e)}"
        }


def compress_uploaded_image(
    image_field,
    jpeg_quality: int = 90
) -> dict:
    """
    Django ImageField ni compress qiladi (model.save() dan keyin ishlatish uchun).
    API kalitlar avtomatik fallback bilan ishlatiladi.
    
    Args:
        image_field: Django ImageField instance
        jpeg_quality: JPEG sifati
    
    Returns:
        dict: compress_image() natijasi
    
    Misol:
        class Product(models.Model):
            image = models.ImageField(upload_to='products/')
            
            def save(self, *args, **kwargs):
                super().save(*args, **kwargs)
                if self.image:
                    compress_uploaded_image(self.image)
    """
    if not image_field:
        return {'success': False, 'message': "Rasm topilmadi"}
    
    return compress_image(
        input_path=image_field.path,
        jpeg_quality=jpeg_quality
    )


def compress_in_memory(
    image_data: bytes,
    filename: str,
    api_key: str = None,
    jpeg_quality: int = 90
) -> dict:
    """
    Xotiradagi rasmni compress qiladi (API upload uchun).
    
    Args:
        image_data: Rasm bytes
        filename: Fayl nomi (format uchun)
        api_key: TinyPNG API kaliti
        jpeg_quality: JPEG sifati
    
    Returns:
        dict: {
            'success': bool,
            'data': bytes (compressed rasm),
            'original_size': int,
            'compressed_size': int,
            'saved_percent': float,
            'message': str
        }
    """
    key = api_key or TINYPNG_API_KEY
    if not key:
        return {
            'success': False,
            'message': "TinyPNG API kaliti topilmadi"
        }
    
    original_size = len(image_data)
    
    try:
        tinify.key = key
        
        # TinyPNG
        source = tinify.from_buffer(image_data)
        compressed_data = source.to_buffer()
        
        # Pillow bilan qo'shimcha optimizatsiya
        img = Image.open(BytesIO(compressed_data))
        ext = os.path.splitext(filename)[1].lower()
        
        output = BytesIO()
        
        if ext in ['.jpg', '.jpeg']:
            img = img.convert("RGB")
            img.save(output, format="JPEG", quality=jpeg_quality, optimize=True, progressive=True)
        elif ext == '.png':
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            img.save(output, format="PNG", optimize=True)
        else:
            img.save(output, optimize=True)
        
        final_data = output.getvalue()
        compressed_size = len(final_data)
        saved_percent = round((1 - compressed_size / original_size) * 100, 2)
        
        return {
            'success': True,
            'data': final_data,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'saved_percent': saved_percent,
            'message': f"✅ {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({saved_percent}% tejaldi)"
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f"❌ Xatolik: {str(e)}"
        }


# ============================================
# Signal orqali avtomatik compress (optional)
# ============================================
def setup_auto_compress(model_class, image_field_name: str, api_key: str = None):
    """
    Model uchun avtomatik compress signal qo'shish.
    
    Misol (apps.py yoki signals.py da):
        from main.image_compressor import setup_auto_compress
        from myapp.models import Product
        
        setup_auto_compress(Product, 'image')
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    
    @receiver(post_save, sender=model_class)
    def auto_compress_image(sender, instance, created, **kwargs):
        image_field = getattr(instance, image_field_name, None)
        if image_field:
            result = compress_uploaded_image(image_field, api_key=api_key)
            if result['success']:
                print(f"[ImageCompressor] {model_class.__name__}: {result['message']}")
