from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class FaceData(models.Model):
    """
    Stores facial data including full name, image, and its embedding vector.
    """
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='face_images/')
    embedding = models.BinaryField()
    created_at = models.DateTimeField(default=timezone.now)

    def full_name(self):
        return " ".join(part for part in [self.first_name, self.middle_name, self.last_name] if part)

    def __str__(self):
        return f"{self.full_name()} ({self.employee_id})"


class UserLog(models.Model):
    """
    Logs actions performed by users, such as admin actions (add, delete, update).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class Attendance(models.Model):
    """
    Stores summary attendance data for each day per face.
    """
    face = models.ForeignKey(FaceData, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.face.full_name()} - {self.date.strftime('%Y-%m-%d')}"


class AttendanceLogEntry(models.Model):
    """
    Logs every IN and OUT event with timestamp for precise duration tracking.
    """
    face = models.ForeignKey(FaceData, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()  # replaces both date and time
    event_type = models.CharField(
        max_length=10,
        choices=[('IN', 'IN'), ('OUT', 'OUT')]
    )

    def __str__(self):
        return f"{self.face.full_name()} - {self.event_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
