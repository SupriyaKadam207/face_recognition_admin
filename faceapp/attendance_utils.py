from .models import Attendance
from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger(__name__)

def log_attendance(face):
    today = date.today()
    now = timezone.now()

    attendance, created = Attendance.objects.get_or_create(face=face, date=today)

    if created:
        attendance.in_time = now
        logger.info(f"[ATTENDANCE] {face.name} entered at {now}")
    else:
        logger.info(f"[ATTENDANCE] {face.name} updated at {now}")

    attendance.out_time = now

    if attendance.in_time and attendance.out_time:
        attendance.duration = attendance.out_time - attendance.in_time

    attendance.save()
