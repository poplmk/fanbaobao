from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from .redis_client import RedisClient
from .response import SuccessResponse, ErrorResponse


@shared_task
def cleanup_expired_data():
    """
    清理过期数据（定时任务）
    """
    from apps.system.models import Notice
    from apps.social.models import FriendApply
    from apps.chat.models import Chat

    try:
        # 清理90天前的已读通知
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        deleted_notices = Notice.objects.filter(
            send_time__lt=ninety_days_ago,
            read_status=1
        ).delete()[0]

        # 清理过期的好友申请（7天）
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        expired_applications = FriendApply.objects.filter(
            apply_status='pending',
            apply_time__lt=seven_days_ago
        ).update(apply_status='expired')

        # 清理过期的缓存键
        cleared_keys = RedisClient.clear_pattern('temp_*')

        return {
            'deleted_notices': deleted_notices,
            'expired_applications': expired_applications,
            'cleared_cache_keys': cleared_keys,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task
def update_popularity_stats():
    """
    更新热度统计（定时任务）
    """
    from apps.stall.models import Stall
    from apps.recommend.models import Recommend

    try:
        # 更新档口热度值
        updated_stalls = 0
        stalls = Stall.objects.filter(is_active=1)
        for stall in stalls:
            stall.update_popularity()
            updated_stalls += 1

        # 更新推荐内容统计
        updated_recommends = 0
        recommends = Recommend.objects.filter(
            audit_status='approved',
            is_deleted=0
        )
        for recommend in recommends:
            # 这里可以添加更新推荐内容统计的逻辑
            pass

        return {
            'updated_stalls': updated_stalls,
            'updated_recommends': updated_recommends,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task
def send_batch_notifications(notice_type, content, target_users=None, jump_url=None):
    """
    批量发送通知（异步任务）
    """
    from apps.system.services import SystemService

    try:
        sent_count = SystemService.send_notification_to_users(
            notice_type, content, jump_url, target_users
        )

        return {
            'sent_count': sent_count,
            'notice_type': notice_type,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task
def process_image_upload(file_data, upload_type):
    """
    处理图片上传（异步任务）
    """
    from .file_upload import FileUploadService
    import base64
    from io import BytesIO

    try:
        # 解码base64文件数据
        file_content = base64.b64decode(file_data)
        file_obj = BytesIO(file_content)

        # 根据上传类型调用不同的方法
        if upload_type == 'avatar':
            file_url = FileUploadService.upload_avatar(file_obj)
        elif upload_type == 'stall':
            file_url = FileUploadService.upload_stall_image(file_obj)
        elif upload_type == 'dish':
            file_url = FileUploadService.upload_dish_image(file_obj)
        elif upload_type == 'recommend':
            file_url = FileUploadService.upload_recommend_image(file_obj)
        else:
            return {'error': '未知的上传类型'}

        return {
            'file_url': file_url,
            'upload_type': upload_type,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task
def backup_database():
    """
    数据库备份（定时任务）
    """
    import subprocess
    import os
    from django.conf import settings

    try:
        # 构建备份文件名
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{timestamp}.sql'
        backup_path = os.path.join(settings.BASE_DIR, 'backups', backup_file)

        # 确保备份目录存在
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        # 执行备份命令（需要根据实际数据库配置调整）
        db_config = settings.DATABASES['default']
        command = [
            'mysqldump',
            '-u', db_config['USER'],
            '-p' + db_config['PASSWORD'],
            '-h', db_config['HOST'],
            '-P', str(db_config['PORT']),
            db_config['NAME'],
            '--result-file=' + backup_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                'backup_file': backup_file,
                'backup_path': backup_path,
                'file_size': os.path.getsize(backup_path) if os.path.exists(backup_path) else 0,
                'timestamp': timezone.now().isoformat()
            }
        else:
            return {'error': result.stderr}

    except Exception as e:
        return {'error': str(e)}


@shared_task
def generate_system_report():
    """
    生成系统报告（定时任务）
    """
    from apps.system.services import SystemService
    from apps.user.models import User

    try:
        # 获取系统统计
        system_stats = SystemService.get_system_overview()

        # 获取用户增长数据
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        new_users = User.objects.filter(
            create_time__gte=thirty_days_ago
        ).count()

        # 获取活跃用户数据（最近7天有登录）
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        active_users = User.objects.filter(
            last_login_time__gte=seven_days_ago
        ).count()

        report_data = {
            'system_stats': system_stats,
            'user_growth': {
                'new_users': new_users,
                'active_users': active_users,
                'total_users': system_stats['total_users']
            },
            'period': '最近30天',
            'generated_at': timezone.now().isoformat()
        }

        # 缓存报告数据
        RedisClient.set('system_report', report_data, 3600)  # 缓存1小时

        return report_data

    except Exception as e:
        return {'error': str(e)}


@shared_task
def test_celery_connection():
    """
    测试Celery连接（用于监控）
    """
    return {
        'status': 'success',
        'message': 'Celery worker is running',
        'timestamp': timezone.now().isoformat()
    }