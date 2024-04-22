"""
Module: nhhc.announcements.models

This module defines a Django model for managing internal announcements within the system.
It includes attributes for message content, announcement title, user who posted the announcement, date posted, message type, and status.
The model provides methods for posting, archiving, and reposting announcements.

Attributes:
- message: TextField - The content of the announcement.
- announcement_title: CharField - The title of the announcement.
- posted_by: ForeignKey to Employee - The user who posted the announcement.
- date_posted: DateTimeField - The date and time when the announcement was posted.
- message_type: CharField - The type of announcement (choices: SAFETY, TRAINING, COMPLIANCE, GENERAL).
- status: CharField - The status of the announcement (choices: ACTIVE, DRAFT, ARCHIVE).

Methods:
- post(request: HttpRequest) -> None: Method to post an announcement instance.
- archive() -> None: Method to delete an announcement instance.
- repost() -> None: Method to repost an announcement instance.

Meta:
- db_table: "announcements"
- ordering: ["-date_posted", "status", "message_type"]
- verbose_name: "Internal Announcement"
- verbose_name_plural: "Internal Announcements"
"""
import arrow
from django.db import models
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _
from django_prometheus.models import ExportModelOperationsMixin
from employee.models import Employee
from loguru import logger

NOW: str = str(arrow.now().format("YYYY-MM-DD"))


class Announcements(models.Model, ExportModelOperationsMixin("announcements")):
    """
    Model representing internal announcements within the system.

    Attributes:
    - message: TextField - The content of the announcement.
    - announcement_title: CharField - The title of the announcement.
    - posted_by: ForeignKey to Employee - The user who posted the announcement.
    - date_posted: DateTimeField - The date and time when the announcement was posted.
    - message_type: CharField - The type of announcement (choices: SAFETY, TRAINING, COMPLIANCE, GENERAL).
    - status: CharField - The status of the announcement (choices: ACTIVE, DRAFT, ARCHIVE).

    Methods:
    - post(request: HttpRequest) -> None: Method to post an announcement instance.
    - archive() -> None: Method to delete an announcement instance.
    - repost() -> None: Method to repost an announcement instance.

    Meta:
    - db_table: "announcements"
    - ordering: ["-date_posted", "status", "message_type"]
    - verbose_name: "Internal Announcement"
    - verbose_name_plural: "Internal Announcements"
    """

    class STATUS(models.TextChoices):
        ACTIVE = "A", _(message="Active")
        DRAFT = "D", _(message="Draft")
        ARCHIVE = "X", _(message="Archived")

    class IMPORTANCE(models.TextChoices):
        SAFETY = "C", _(message="Safety")
        TRAINING = "T", _(message="Training")
        COMPLIANCE = "X", _(message="Compliance")
        GENERAL = "G", _(message="General")

    message = models.TextField()
    announcement_title = models.CharField(max_length=255, default="")
    posted_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    date_posted = models.DateTimeField(auto_now=True)
    message_type = models.CharField(
        max_length=255,
        choices=IMPORTANCE.choices,
        default=IMPORTANCE.GENERAL,
    )
    status = models.CharField(
        max_length=255,
        choices=STATUS.choices,
        default=STATUS.DRAFT,
    )

    def post(self, request: HttpRequest) -> None:
        """
        Method to post an annoucement instance.

        Args:
        - request: HttpRequest object containing the request data

        Returns:
        - None

        This method sets the 'posted_by' attribute to the user id from the request,
        sets the 'status' attribute to 'ACTIVE', saves the object, and logs the success or error message.
        """
        try:
            self.posted_by = request.user.employee_id
            self.status = "A"
            self.save()
            logger.success(f"Succesfully posted {self.pk}")
        except Exception as e:
            if self.pk is None:
                logger.error(f"ERROR: Unable to post - ID is unavaliable - Post JSON ()")
            logger.error(f"ERROR: Unable to post {self.pk} - {e}")

    def archive(self) -> None:
        """
        Method to delete an annoucement instance.

        This method sets the status of the object to 'ARCHIVE', saves the object, and logs a success message if successful.
        If an exception occurs during the deletion process, an error message is logged.
        """
        try:
            self.status = "X"
            self.save()
            logger.success(f"Succesfully deleted {self.pk}")
        except Exception as e:
            logger.error(f"ERROR: Unable to delete {self.pk} - {e}")

    def repost(self) -> None:
        """
        Reposts an annoucemen t post by updating the date_posted, status, and saving the changes.

        Args
        - self: the current instance of the post

        Returns:
        - None

        Logs a success message if the repost is successful, otherwise logs an error message.
        """
        try:
            self.date_posted = NOW
            self.status = self.STATUS.ACTIVE
            self.save()
            logger.success(f"Succesfully reposted {self.pk}")
        except Exception as e:
            logger.error(f"ERROR: Unable to repost {self.pk} - {e}")

    class Meta:
        db_table = "announcements"
        ordering = ["-date_posted", "status", "message_type"]
        verbose_name = "Internal Announcement"
        verbose_name_plural = "Internal Announcements"
