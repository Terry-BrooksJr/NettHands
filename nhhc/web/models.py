"""
Module: Web.Models

This module contains the models needed for the front-end for client interest submissions and employment applications.

ClientInterestSubmissions:
- Represents the model for client interest submissions.
- Fields include first_name, last_name, email, contact_number, zipcode, insurance_carrier, desired_service, date_submitted, reviewed, reviewed_by.

EmploymentApplicationModel:
- Represents the model for employment applications.
- Fields include first_name, last_name, contact_number, email, home_address, city, state, zipcode, mobility, prior_experience, ipdh_registered, availability_monday, availability_tuesday, availability_wednesday, availability_thursday, availability_friday, availability_saturday, availability_sunday, reviewed, hired, reviewed_by, date_submitted.

Both models have methods for marking as reviewed, hiring an applicant, and rejecting an applicant.

Note: The module also includes choices for services, mobility, and prior experience.

"""

import datetime
import random
import string
import json

import arrow
from compliance.models import Compliance
from django.contrib.auth.hashers import make_password
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_prometheus.models import ExportModelOperationsMixin
from employee.models import Employee
from localflavor.us.models import USStateField, USZipCodeField
from loguru import logger
from phonenumber_field.modelfields import PhoneNumberField
from authentication.models import RandomPasswordGenerator

now = arrow.now(tz="US/Central")


class ClientInterestSubmissions(
    models.Model, ExportModelOperationsMixin("client_inquiries")
):
    def __str__(self):
        return f"{self.last_name}, {self.first_name} - Submission Date: {arrow.get(self.date_submitted).format('YYYY-MM-DD')}"

    class SERVICES(models.TextChoices):
        INTERMITTENT = "I", _("Intermittent Home Care")
        NONMEDICAL = "NM", _("Non-Medical Home Care")
        MEDICAL_SW = "MSW", _("Medical Social Work")
        OCCUP_THERAPY = "OT", _("Occupational Therapy")
        PHYS_THERAPY = "PT", _("Physical Therapy")
        OTHER = "NA", _("Other")

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(null=True)
    contact_number = PhoneNumberField(region="US")
    home_address1 = models.CharField(max_length=800, null=True)
    home_address2 = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    zipcode = USZipCodeField(null=True, blank=True)
    state = USStateField(max_length=2, null=True, blank=True)
    insurance_carrier = models.CharField(max_length=255)
    desired_service = models.CharField(max_length=255, choices=SERVICES.choices)
    date_submitted = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    def marked_reviewed(self, user_id: Employee) -> None:
        """Marks the review as reviewed by the specified user.

        Args:
            user_id (Employee): The ID of the user who reviewed the item.

        Returns:
            None
        """
        self.reviewed = True
        self.reviewed_by = user_id

    class Meta:
        db_table = "interest_clients"
        ordering = ["last_name", "first_name", "date_submitted"]
        verbose_name = "Interested Client"
        verbose_name_plural = "Interested Clients"


class EmploymentApplicationModel(
    models.Model, ExportModelOperationsMixin("applications")
):
    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.id}) - Submission Date: {arrow.get(self.date_submitted).format('YYYY-MM-DD')}"

    class MOBILITTY(models.TextChoices):
        CAR = "C", _("I Have Consistent Access To A Car")
        PUBLIC = "P", _("I Use Public Transportation")
        RIDE_SHARE = "RS", _(
            "I Use Rideshare (Uber/Lyft) or a Reliable Pickup/Dropoff Provider",
        )
        OTHER = "NA", _("Other")

    class PRIOREXPERIENCE(models.TextChoices):
        SENIOR = "S", _("12+ Months")
        JUNIOR = "J", _("3+ Months")
        NEW = "N", _("No Prior Experience")

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    contact_number = PhoneNumberField(region="US")
    email = models.EmailField(max_length=254)
    home_address1 = models.CharField(max_length=800)
    home_address2 = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(
        max_length=255,
    )
    state = USStateField(max_length=2)
    zipcode = USZipCodeField()
    mobility = models.CharField(max_length=255, choices=MOBILITTY.choices)
    prior_experience = models.CharField(max_length=255, choices=PRIOREXPERIENCE.choices)
    ipdh_registered = models.BooleanField(default=False)
    availability_monday = models.BooleanField(null=True, blank=True)
    availability_tuesday = models.BooleanField(null=True, blank=True)
    availability_wednesday = models.BooleanField(null=True, blank=True)
    availability_thursday = models.BooleanField(null=True, blank=True)
    availability_friday = models.BooleanField(null=True, blank=True)
    availability_saturday = models.BooleanField(null=True, blank=True)
    availability_sunday = models.BooleanField(null=True, blank=True)
    reviewed = models.BooleanField(null=True, blank=True, default=False)
    hired = models.BooleanField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    date_submitted = models.DateTimeField(auto_now_add=True)

    def hire_applicant(self, hired_by: Employee) -> None:
        """
        Hire a new employee by creating a user account, generating a random password, and saving employee and compliance information in the database.

        Args:
          hired_by (str): The user who is hiring the applicant.

        Returns:
        None

        Raises:
        Exception: If an error occurs during the hiring process.

        Example:
        # Create an instance of the Applicant class
        applicant = Applicant(first_name='John', last_name='Doe', email='john.doe@example.com', contact_number='123-456-7890')
        # Hire the applicant
        applicant.hire_applicant(hired_by='HR_Manager')
        """
        try:
            username = (
                f"{self.first_name.lower()}.{self.last_name.lower().replace(' ', '.')}"
            )
            new_employee = Employee(
                is_superuser=False,
                username=Employee.create_unique_username(
                    self.first_name, self.last_name
                ),
                is_active=True,
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                phone=self.contact_number,
                street_address1=self.home_address1,
                street_address2=self.home_address2,
                state=self.state,
                city=self.city,
                zipcode=self.zipcode,
            )
            password = RandomPasswordGenerator.generate()
            new_employee.password = make_password(password)
            new_employee.save()
            compliance = Compliance(employee=new_employee)
            compliance.save()
            self.hired = True
            self.reviewed = True
            self.reviewed_by = hired_by
            return {
                "user": new_employee,
                "plain_text_password": password,
                "username": new_employee.username
            }
        except Exception as e:
            log_message = (
                f"Unable to Hire {self.last_name},{self.first_name} - REASON:{e} "
            )
            logger.error(log_message)
            raise RuntimeError from e
        
    def reject_applicant(self, rejected_by: Employee) -> None:
        """Rejects an applicant.

        Args:
            rejected_by (Employee): The employee who rejected the applicant.

        Returns:
            None
        """
        self.hired = False
        self.reviewed = True
        self.reviewed_by = rejected_by

    class Meta:
        db_table = "employment_interests"
        ordering = ["last_name", "first_name", "date_submitted"]
        verbose_name = "Prospective Employee"
        verbose_name_plural = "Prospective Employees"
