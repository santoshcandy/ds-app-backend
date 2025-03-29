
from datetime import date
# Create your models here.
from django.contrib.auth import get_user_model
from django.db import models
import os
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
# User = get_user_model()  # Secure way to reference User model dynamically

class UserManager(BaseUserManager):
    def create_user(self, username, email, phone_number, dob, role, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not phone_number:
            raise ValueError("Users must have a phone number")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            phone_number=phone_number,
            dob=dob,
            role=role
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, phone_number, dob, password):
        user = self.create_user(username, email, phone_number, dob, role="manager", password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
    )

    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True , null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone_number", "dob"]

    def __str__(self):
        return f"{self.username} ({self.role})"

# ✅ Client Model (For Both Direct & Employee-Registered Clients)
class Client(models.Model):
    CLIENT_TYPE_CHOICES = (
        ('direct', 'Direct Client'),
        ('employee_registered', 'Employee-Registered Client'),
    )

    name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15, unique=True)
    alternative_number = models.CharField(max_length=15, blank=True, null=True)
    father_name = models.CharField(max_length=255)
    mother_name = models.CharField(max_length=255)
    qualifications = models.CharField(max_length=255)
    married_status = models.BooleanField(default=False)
    current_address = models.TextField()
    landmark = models.CharField(max_length=255)
    years_at_address = models.IntegerField()
    gmail = models.EmailField(unique=True)
    office_name = models.CharField(max_length=255)
    office_address = models.TextField()
    designation = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, null=True)
    current_experience = models.IntegerField()  # In years
    overall_experience = models.IntegerField()  # In years
    reference_name_1 = models.CharField(max_length=255)
    reference_number_1 = models.CharField(max_length=15)
    reference_name_2 = models.CharField(max_length=255)
    reference_number_2 = models.CharField(max_length=15)
    expected_loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    loan_purpose = models.TextField()

    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, default='direct')

    # ✅ Clients are assigned to Employees
    assigned_employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
        limit_choices_to={'role': 'employee'}  # Ensures only employees are assigned
    )

    status_choices = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    approval_status = models.CharField(max_length=10, choices=status_choices, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.client_type}) - {self.assigned_employee if self.assigned_employee else 'Unassigned'}"



def client_document_path(instance, filename):
    """
    Store files in a dedicated folder: media/documents/client_<id>/
    """
    return os.path.join(f"documents/client_{instance.client.id}/", filename)

class EmployeeClientDetails(models.Model):
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="extra_details"
    )

    # ✅ Save files inside a dedicated client folder
    cibil_score = models.IntegerField(null=True, blank=True)
    aadhaar_front = models.ImageField(upload_to=client_document_path, null=True, blank=True)
    aadhaar_back = models.ImageField(upload_to=client_document_path, null=True, blank=True)
    cibil_report = models.ImageField(upload_to=client_document_path, null=True, blank=True)
    pan_card = models.ImageField(upload_to=client_document_path, null=True, blank=True)
    gas_bill = models.ImageField(upload_to=client_document_path, null=True, blank=True)

    reference_number_1 = models.CharField(max_length=15)
    reference_number_2 = models.CharField(max_length=15)

    filled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filled_client_details",
        limit_choices_to={'role': 'employee'}
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Details for {self.client.name} (Filled by {self.filled_by.username if self.filled_by else 'Unknown'})"
 


 
class Attendance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent')])

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.status}"
    

class MonthlyTarget(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True,  # Allow null for "all employees"
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'employee'}
    )
    month = models.IntegerField(default=date.today().month)  # Default current month
    year = models.IntegerField(default=date.today().year)  # Default current year
    target_clients = models.IntegerField()  # Number of clients to approve
    approved_clients = models.IntegerField(default=0)  # Auto-updated count

    class Meta:
        unique_together = ('user', 'month', 'year')  # Ensure only one target per user per month

    def update_approved_clients(self):
        """Auto-updates the approved client count based on the Client model."""
        from app.models import Client  # Avoid circular imports

        # Ensure update only happens for specific employees
        if self.user:
            approved_count = Client.objects.filter(
                assigned_employee=self.user,
                approval_status="approved",
                created_at__month=self.month,
                created_at__year=self.year
            ).count()

            if self.approved_clients != approved_count:  # Prevent unnecessary updates
                self.approved_clients = approved_count
                MonthlyTarget.objects.filter(pk=self.pk).update(approved_clients=approved_count)

    def save(self, *args, **kwargs):
        """Ensure approved_clients count is updated correctly."""
        super().save(*args, **kwargs)  # Normal save
        self.update_approved_clients()  # Update approvals only after save

        # If user is null, create targets for all employees
        if self.user is None:
            employees = User.objects.filter(role="employee")
            for emp in employees:
                MonthlyTarget.objects.update_or_create(
                    user=emp, month=self.month, year=self.year,
                    defaults={"target_clients": self.target_clients}
                )

    def __str__(self):
        return f"{self.user.username if self.user else 'All Employees'} - {self.month}/{self.year} (Target: {self.target_clients}, Approved: {self.approved_clients})"