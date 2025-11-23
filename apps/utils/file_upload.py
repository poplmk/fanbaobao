import os
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image
import magic
from .exceptions import BusinessException


class FileUploadService:
    """文件上传服务类"""

    @staticmethod
    def validate_image(file):
        """
        验证图片文件
        """
        # 检查文件大小
        if file.size > settings.FILE_UPLOAD_CONFIG['MAX_IMAGE_SIZE']:
            raise ValidationError(f"图片大小不能超过{settings.FILE_UPLOAD_CONFIG['MAX_IMAGE_SIZE'] // 1024 // 1024}MB")

        # 检查文件类型
        file_type = magic.from_buffer(file.read(1024), mime=True)
        if file_type not in settings.FILE_UPLOAD_CONFIG['ALLOWED_IMAGE_TYPES']:
            raise ValidationError("不支持的文件类型")

        # 重置文件指针
        file.seek(0)

        # 验证图片格式
        try:
            image = Image.open(file)
            image.verify()
            file.seek(0)
        except Exception:
            raise ValidationError("无效的图片文件")

        return True

    @staticmethod
    def save_image(file, upload_path, resize=None):
        """
        保存图片文件
        """
        try:
            # 生成唯一文件名
            file_extension = os.path.splitext(file.name)[1]
            filename = f"{uuid.uuid4().hex}{file_extension}"

            # 构建完整路径
            full_path = os.path.join(upload_path, filename)

            # 如果需要调整大小
            if resize:
                image = Image.open(file)
                if image.mode in ('RGBA', 'LA'):
                    # 处理透明背景
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background

                image.thumbnail(resize, Image.Resampling.LANCZOS)

                # 保存调整大小后的图片
                from io import BytesIO
                output = BytesIO()
                image.save(output, format='JPEG', quality=85)
                output.seek(0)

                saved_path = default_storage.save(full_path, ContentFile(output.read()))
            else:
                saved_path = default_storage.save(full_path, ContentFile(file.read()))

            # 返回文件URL
            return default_storage.url(saved_path)

        except Exception as e:
            raise BusinessException(f"文件上传失败: {str(e)}")

    @staticmethod
    def upload_avatar(file):
        """
        上传用户头像
        """
        FileUploadService.validate_image(file)
        return FileUploadService.save_image(
            file,
            settings.FILE_UPLOAD_CONFIG['AVATAR_UPLOAD_PATH'],
            resize=(200, 200)  # 头像调整为200x200
        )

    @staticmethod
    def upload_stall_image(file):
        """
        上传档口图片
        """
        FileUploadService.validate_image(file)
        return FileUploadService.save_image(
            file,
            settings.FILE_UPLOAD_CONFIG['STALL_UPLOAD_PATH'],
            resize=(800, 600)  # 档口图片调整为800x600
        )

    @staticmethod
    def upload_dish_image(file):
        """
        上传菜品图片
        """
        FileUploadService.validate_image(file)
        return FileUploadService.save_image(
            file,
            settings.FILE_UPLOAD_CONFIG['DISH_UPLOAD_PATH'],
            resize=(600, 400)  # 菜品图片调整为600x400
        )

    @staticmethod
    def upload_recommend_image(file):
        """
        上传推荐内容图片
        """
        FileUploadService.validate_image(file)
        return FileUploadService.save_image(
            file,
            settings.FILE_UPLOAD_CONFIG['RECOMMEND_UPLOAD_PATH'],
            resize=(1000, 750)  # 推荐图片调整为1000x750
        )

    @staticmethod
    def delete_file(file_url):
        """
        删除文件
        """
        try:
            if file_url.startswith(settings.MEDIA_URL):
                file_path = file_url.replace(settings.MEDIA_URL, '', 1)
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def cleanup_orphaned_files():
        """
        清理孤儿文件（定时任务）
        """
        # 这里可以实现清理未被任何记录引用的文件
        # 需要根据具体业务逻辑实现
        pass