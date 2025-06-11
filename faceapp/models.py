from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class FaceData(models.Model):
    """
    Stores facial data including name, image, and its embedding vector.
    """
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='face_images/')
    embedding = models.BinaryField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class UserLog(models.Model):
    """
    Logs actions performed by users (e.g., admin actions like add/delete).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"


class Attendance(models.Model):
    """
    Tracks attendance based on recognition events: in-time, out-time, and duration.
    Linked to FaceData for registered faces.
    """
    face = models.ForeignKey(FaceData, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    in_time = models.DateTimeField(null=True, blank=True)  # ✅ Fixed here
    out_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.face.name} - {self.date}"
