from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.timezone import now
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date

from .models import FaceData, UserLog, Attendance
from face_recognition_module.faiss_test import run_faiss_recognition, run_faiss_recognition_from_frame
from face_recognition_module.video_stream import VideoStream
from faceapp.attendance_utils import log_attendance

from datetime import datetime, timedelta, time as dt_time
import threading
import cv2
import time

from xhtml2pdf import pisa
from openpyxl import Workbook
import io  # ✅ for Excel streaming safety

# ------------------ Admin Dashboard ------------------

@login_required
def custom_admin_view(request):
    if request.method == 'POST' and 'delete_id' not in request.POST:
        name = request.POST.get('name')
        image = request.FILES.get('image')
        if name and image:
            face = FaceData(name=name, image=image)
            face.save()
            UserLog.objects.create(user=request.user, action=f"Added user: {name}")
            return redirect('custom_admin')

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')
    faces = FaceData.objects.all()

    if search_query:
        faces = faces.filter(Q(name__icontains=search_query))

    if sort_by == 'date':
        faces = faces.order_by('-id')
    else:
        faces = faces.order_by('name')

    return render(request, 'custom_admin.html', {
        'faces': faces,
        'search_query': search_query,
        'sort_by': sort_by
    })


@login_required
def delete_face(request, face_id):
    if request.method == 'POST':
        face = get_object_or_404(FaceData, id=face_id)
        face_name = face.name
        face.delete()
        UserLog.objects.create(user=request.user, action=f"Deleted user: {face_name}")
    return redirect('custom_admin')


@login_required
def update_face(request, face_id):
    face = get_object_or_404(FaceData, id=face_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')
        if name:
            face.name = name
        if image:
            face.image = image
        face.save()
        UserLog.objects.create(user=request.user, action=f"Updated user: {face.name}")
        return redirect('custom_admin')
    return render(request, 'update_face.html', {'face': face})


# ------------------ Logs ------------------

@login_required
def view_logs(request):
    if request.user.is_superuser:
        logs = UserLog.objects.all().order_by('-timestamp')
    else:
        logs = UserLog.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'view_logs.html', {'logs': logs})


# ------------------ Face Recognition ------------------

@login_required
def start_faiss_recognition(request):
    thread = threading.Thread(target=run_faiss_recognition, daemon=True)
    thread.start()
    return HttpResponse("✅ FAISS Face Recognition started.")


@login_required
def video_feed(request):
    stream = VideoStream("rtsp://srivitest:Work$789@192.168.1.37:554/streaming/channels/0601")

    def generate():
        frame_count = 0
        try:
            while True:
                ret, frame = stream.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

                frame_count += 1
                if frame_count % 2 != 0:
                    continue

                try:
                    faces = run_faiss_recognition_from_frame(frame)
                except Exception as e:
                    print(f"Recognition error: {e}")
                    faces = []

                for (x, y, w, h, name) in faces:
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    if name != "Unknown":
                        try:
                            face_obj = FaceData.objects.get(name=name)
                            log_attendance(face_obj)
                        except FaceData.DoesNotExist:
                            print(f"{name} not found in FaceData.")
                        except Exception as e:
                            print(f"Logging error for {name}: {e}")

                success, jpeg = cv2.imencode('.jpg', frame)
                if not success:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        finally:
            stream.release()

    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace; boundary=frame')


# ------------------ Attendance ------------------

@login_required
def attendance_logs(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    logs = Attendance.objects.select_related('face').all()

    if not request.user.is_superuser:
        logs = logs.filter(face__name=request.user.username)

    # Filter by date range
    if from_date:
        from_date_obj = parse_date(from_date)
        if from_date_obj:
            logs = logs.filter(date__gte=from_date_obj)

    if to_date:
        to_date_obj = parse_date(to_date)
        if to_date_obj:
            logs = logs.filter(date__lte=to_date_obj)

    logs = logs.order_by('-date', 'face__name')

    return render(request, 'attendance_logs.html', {
        'logs': logs,
        'from_date': from_date,
        'to_date': to_date
    })


def get_attendance_summary_queryset(request):
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')

    from_date = parse_date(from_date) if from_date not in [None, '', 'None'] else None
    to_date = parse_date(to_date) if to_date not in [None, '', 'None'] else None

    queryset = Attendance.objects.select_related('face').all()
    if from_date and to_date:
        queryset = queryset.filter(date__range=[from_date, to_date])
    return queryset, from_date, to_date


def build_summary(queryset):
    summary = {}
    for record in queryset:
        name = record.face.name
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

    all_faces = set(FaceData.objects.values_list('name', flat=True))
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
