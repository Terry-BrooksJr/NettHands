from collections.abc import Callable
from uuid import uuid4

from compliance.models import Compliance
from django.conf import settings
from django.db import models
from django.db.models import signals
from employee.models import Employee
from loguru import logger

logger.add(
    settings.DEBUG_LOG_FILE, diagnose=True, catch=True, backtrace=True, level="DEBUG"
)
logger.add(
    settings.PRIMARY_LOG_FILE, diagnose=False, catch=True, backtrace=False, level="INFO"
)
logger.add(
    settings.LOGTAIL_HANDLER, diagnose=False, catch=True, backtrace=False, level="INFO"
)


class UserProfile(models.Model):
    user = models.OneToOneField(Employee, unique=True, on_delete=models.CASCADE)
    force_password_change = models.BooleanField(default=True)
    last_password_change = models.DateTimeField(auto_now_add=True)


def create_user_profile_signal(sender: Callable, instance, created, **kwargs) -> None:
    if created:
        UserProfile.objects.create(user=instance)
        logger.debug(f"Signal Triggered for UserProfile Creation for {instance}")
        Compliance.objects.create(employee=instance)
        logger.debug(f"Signal Triggered for Compliance Creation for {instance}")


def password_change_signal(sender, instance, **kwargs) -> None:
    try:
        user = Employee.objects.get(username=instance.username)
        if not user.password == instance.password:
            profile = user.get_profile()
            profile.force_password_change = False
            profile.save()
    except Employee.DoesNotExist:
        pass


signals.pre_save.connect(
    password_change_signal,
    sender=Employee,
    dispatch_uid=f"employee.models + {str(uuid4())}",
)

signals.post_save.connect(
    create_user_profile_signal,
    sender=Employee,
    dispatch_uid=f"employee.models + {str(uuid4())}",
)
