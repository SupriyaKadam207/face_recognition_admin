from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.timezone import now, localtime
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date

from .models import FaceData, UserLog, Attendance
from face_recognition_module import run_faiss_recognition_from_frame
from datetime import datetime, time as dt_time, timedelta
from xhtml2pdf import pisa
from openpyxl import Workbook

import cv2
import threading
import time
import io

# ------------------ Threaded Video Capture ------------------

class VideoCamera:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.ret, self.frame = self.cap.read()
        self.running = True
        threading.Thread(target=self.update_frame, daemon=True).start()

    def update_frame(self):
        while self.running:
            self.ret, self.frame = self.cap.read()
            time.sleep(0.01)

    def get_frame(self):
        return self.ret, self.frame

    def release(self):
        self.running = False
        self.cap.release()


# ------------------ Admin Dashboard ------------------

@login_required
def custom_admin_view(request):
    if request.method == 'POST' and 'delete_id' not in request.POST:
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        image = request.FILES.get('image')

        if first_name and image:
            face = FaceData(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                image=image
            )
            face.save()
            UserLog.objects.create(user=request.user, action=f"Added user: {face.full_name()}")
            return redirect('custom_admin')

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'first_name')
    faces = FaceData.objects.all()

    if search_query:
        faces = faces.filter(
            Q(first_name__icontains=search_query) |
            Q(middle_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    if sort_by == 'date':
        faces = faces.order_by('-id')
    else:
        faces = faces.order_by('first_name')

    return render(request, 'custom_admin.html', {
        'faces': faces,
        'search_query': search_query,
        'sort_by': sort_by
    })


@login_required
def delete_face(request, face_id):
    if request.method == 'POST':
        face = get_object_or_404(FaceData, id=face_id)
        full_name = face.full_name()
        face.delete()
        UserLog.objects.create(user=request.user, action=f"Deleted user: {full_name}")
    return redirect('custom_admin')


@login_required
def update_face(request, face_id):
    face = get_object_or_404(FaceData, id=face_id)
    if request.method == 'POST':
        face.first_name = request.POST.get('first_name')
        face.middle_name = request.POST.get('middle_name')
        face.last_name = request.POST.get('last_name')
        image = request.FILES.get('image')
        if image:
            face.image = image
        face.save()
        UserLog.objects.create(user=request.user, action=f"Updated user: {face.full_name()}")
        return redirect('custom_admin')
    return render(request, 'update_face.html', {'face': face})


# ------------------ Logs ------------------

@login_required
def view_logs(request):
    logs = UserLog.objects.all().order_by('-timestamp') if request.user.is_superuser else UserLog.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'view_logs.html', {'logs': logs})


# ------------------ Face Recognition ------------------

@login_required
def start_faiss_recognition(request):
    threading.Thread(target=run_faiss_recognition, daemon=True).start()
    return HttpResponse("✅ FAISS Face Recognition started.")


@login_required
def video_feed(request):
    camera = VideoCamera("rtsp://srivitest:Work$789@192.168.1.37:554/streaming/channels/0601")

    def generate():
        frame_count = 0
        try:
            while True:
                ret, frame = camera.get_frame()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

                frame_count += 1
                if frame_count % 2 != 0:
                    continue

                try:
                    faces = run_faiss_recognition_from_frame(frame)
                except Exception as e:
                    print(f"[Recognition Error] {e}")
                    faces = []

                for (x, y, w, h, name) in faces:
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    if name != "Unknown":
                        try:
                            face_obj = FaceData.objects.get(first_name=name)
                            log_attendance(face_obj)
                        except FaceData.DoesNotExist:
                            print(f"[Warning] {name} not found in FaceData.")
                        except Exception as e:
                            print(f"[Attendance Logging Error for {name}] {e}")

                success, jpeg = cv2.imencode('.jpg', frame)
                if not success:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        finally:
            camera.release()

    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace; boundary=frame')


# ------------------ Attendance ------------------

def log_attendance(face_obj):
    today = now().date()
    current_time = timezone.localtime()

    attendance, created = Attendance.objects.get_or_create(face=face_obj, date=today)

    if attendance.in_time is None:
        attendance.in_time = current_time
    else:
        attendance.out_time = current_time
        if attendance.in_time and attendance.out_time:
            attendance.duration = attendance.out_time - attendance.in_time  # ✅ Correct calculation

    attendance.save()


@login_required
def attendance_logs(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    logs = Attendance.objects.select_related('face').all()
    if not request.user.is_superuser:
        logs = logs.filter(face__first_name=request.user.username)

    if from_date:
        from_date_obj = parse_date(from_date)
        if from_date_obj:
            logs = logs.filter(date__gte=from_date_obj)

    if to_date:
        to_date_obj = parse_date(to_date)
        if to_date_obj:
            logs = logs.filter(date__lte=to_date_obj)

    logs = logs.order_by('-date', 'face__first_name')

    return render(request, 'attendance_logs.html', {
        'logs': logs,
        'from_date': from_date,
        'to_date': to_date
    })


# ------------------ Attendance Summary ------------------

def get_attendance_summary_queryset(request):
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    from_date = parse_date(from_date) if from_date else None
    to_date = parse_date(to_date) if to_date else None

    queryset = Attendance.objects.select_related('face').all()
    if from_date and to_date:
        queryset = queryset.filter(date__range=[from_date, to_date])
    return queryset, from_date, to_date


def build_summary(queryset):
    summary = {}
    for record in queryset:
        name = record.face.full_name()
        if name not in summary:
            summary[name] = {
                'days_present': 0,
                'total_duration': timedelta(),
                'late_days': 0
            }
        summary[name]['days_present'] += 1
        summary[name]['total_duration'] += record.duration or timedelta()
        if record.in_time and record.in_time.time() > dt_time(10, 0):
            summary[name]['late_days'] += 1
    return summary


@login_required
def attendance_summary(request):
    queryset, from_date, to_date = get_attendance_summary_queryset(request)
    summary = build_summary(queryset)

    all_faces = set([f.full_name() for f in FaceData.objects.all()])
    present_faces = set(summary.keys())
    absent_users = all_faces - present_faces

    return render(request, 'attendance_summary.html', {
        'summary': summary,
        'absent_users': absent_users,
        'from_date': from_date,
        'to_date': to_date
    })


# ------------------ Export Reports ------------------

@login_required
def export_attendance_pdf(request):
    queryset, from_date, to_date = get_attendance_summary_queryset(request)
    summary = build_summary(queryset)

    html = render_to_string('attendance_pdf_template.html', {'summary': summary})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="attendance_summary.pdf"'

    result = pisa.CreatePDF(src=html, dest=response)
    if result.err:
        return HttpResponse('Error generating PDF', status=500)
    return response


@login_required
def export_attendance_excel(request):
    queryset, from_date, to_date = get_attendance_summary_queryset(request)
    summary = build_summary(queryset)

    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Summary"
    ws.append(["Name", "Days Present", "Total Duration", "Late Days"])

    for name, data in summary.items():
        duration_str = str(data['total_duration']).split('.')[0] if data['total_duration'] else "00:00:00"
        ws.append([name, data['days_present'], duration_str, data['late_days']])

    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="attendance_summary.xlsx"'
    return response
