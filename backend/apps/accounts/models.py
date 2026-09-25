from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Platform staff/admin user. Customers are NOT required to register an
    account for the MVP (search and enquiry submission work anonymously);
    this model exists for admin dashboard operators and, later, for
    optional customer accounts (saved properties, lead history).
    """

    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super Admin"
        VERIFICATION_OFFICER = "VERIFICATION_OFFICER", "Verification Officer"
        SUPPORT = "SUPPORT", "Support"
        CUSTOMER = "CUSTOMER", "Customer"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.CUSTOMER)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.email or self.username

    @property
    def is_staff_role(self):
        return self.role in {self.Role.SUPERADMIN, self.Role.VERIFICATION_OFFICER, self.Role.SUPPORT}
