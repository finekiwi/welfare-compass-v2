from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = '알림'
    
    def ready(self):
        # 시그널 등록
        import notifications.signals  # noqa: F401
