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
    created_at = models.DateTimeField(default=timezone.now)  # Added for filtering/sorting by date

    def __str__(self):
        return self.name


class UserLog(models.Model):
    """
    Logs actions performed by users (e.g., admin adding or deleting faces).
    Also tracks session durations (e.g., how long a user was logged in).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)  # New field for session duration

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
