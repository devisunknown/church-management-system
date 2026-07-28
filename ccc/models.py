from django.db import models
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField

class _EmptyRelatedManager:
    def all(self):
        return []


class members(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    age=models.IntegerField(null=True, blank=True)
    residence=models.CharField(max_length=80,default=None)
    ministration = models.CharField(max_length=100)
    role=models.CharField(max_length=100)
    membership_status=models.CharField(max_length=100, default='active')
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    scd_group=models.CharField(max_length=100)
    datejoined=models.DateTimeField(null=True)
    dateofbirth=models.DateTimeField(null=True)
    image = CloudinaryField('image', null=True, blank=True)
    notes = models.TextField(default='', blank=True)

    @property
    def full_name(self):
        return f"{self.firstname} {self.lastname}".strip()

    @property
    def status(self):
        return self.membership_status or 'active'

    @property
    def date_joined(self):
        return self.datejoined

    @property
    def phone(self):
        return self.phone_number

    @property
    def photo(self):
        return self.image

    @property
    def initials(self):
        parts = [part for part in self.full_name.split() if part]
        if not parts:
            return ''
        return ''.join(part[0].upper() for part in parts[:2])

    @property
    def attendance_percentage(self):
        return None

    @property
    def groups(self):
        return _EmptyRelatedManager()

    @property
    def serving_areas(self):
        return _EmptyRelatedManager()

    def __str__(self):
        return self.firstname


class event(models.Model):
    tittle=models.CharField(max_length=100)
    description=models.CharField(max_length=100)
    date=models.DateTimeField(null=True)
    starttime=models.TimeField(null=True)
    endtime=models.TimeField(null=True)
    location=models.CharField(max_length=60)
    category=models.CharField(max_length=10)

    @property
    def title(self):
        return self.tittle

    @property
    def start_time(self):
        return self.starttime

    @property
    def end_time(self):
        return self.endtime

    @property
    def registration_open(self):
        return False

    @property
    def booked_count(self):
        return 0

    @property
    def capacity(self):
        return 0



class attendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(members, on_delete=models.CASCADE, related_name='attendance_records')
    event = models.ForeignKey(event, on_delete=models.CASCADE, related_name='attendance_records')
    is_present = models.BooleanField(default=False)
    marked_by = models.CharField(max_length=100, blank=True, null=True)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('member', 'event')



class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ('member_added', 'New Member'),
        ('event_created', 'Event Created'),
        ('attendance_taken', 'Attendance Taken'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    actor = models.CharField(max_length=150, blank=True, default='')
    icon = models.CharField(max_length=50, default='info')  # material symbol name
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_type}: {self.description}"


class GivingRecord(models.Model):
    FUND_CHOICES = [
        ('general', 'General Fund'),
        ('building', 'Building Fund'),
        ('missions', 'Missions'),
        ('youth', 'Youth Ministry'),
        ('benevolence', 'Benevolence'),
    ]

    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('ach', 'ACH'),
        ('card', 'Card'),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Donation'),
        ('expense', 'Deduction'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, default='income')
    donor_name = models.CharField(max_length=150, blank=True)
    fund = models.CharField(max_length=30, choices=FUND_CHOICES, default='general')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash')
    gift_date = models.DateField(default=timezone.localdate)
    tax_deductible = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_deduction(self):
        return self.transaction_type == 'expense'

    @property
    def signed_amount(self):
        """Amount signed for net calculations: negative for deductions."""
        return -self.amount if self.is_deduction else self.amount

    def __str__(self):
        label = 'Deduction' if self.is_deduction else 'Gift'
        return f"{label}: {self.amount} ({self.fund})"
