from django.shortcuts import render, redirect, get_object_or_404
from .models import FaceData, UserLog
from django.contrib.auth.decorators import login_required
from django.utils.timezone import timedelta
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
import threading
import cv2

# Import your recognition functions
from face_recognition_module.test import run_recognition
from face_recognition_module.faiss_test import run_faiss_recognition


@login_required
def custom_admin_view(request):
    if request.method == 'POST' and 'delete_id' not in request.POST:
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if name and image:
            face = FaceData(name=name, image=image)
            face.save()

            UserLog.objects.create(
                user=request.user,
                action=f"Added user: {name}"
            )

            return redirect('custom_admin')

    # --- Search and Sort Logic ---
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')

    faces = FaceData.objects.all()

    if search_query:
        faces = faces.filter(Q(name__icontains=search_query))

    if sort_by == 'date':
        faces = faces.order_by('-id')  # Use created_at if available
    elif sort_by == 'name':
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

        UserLog.objects.create(
            user=request.user,
            action=f"Deleted user: {face_name}"
        )

    return redirect('custom_admin')


@login_required
def view_logs(request):
    if request.user.is_superuser:
        logs = UserLog.objects.all().order_by('-timestamp')
        user_log_times = {}

        for log in logs:
            if log.duration:
                if log.user not in user_log_times:
                    user_log_times[log.user] = timedelta()
                user_log_times[log.user] += log.duration

        logs_with_total_time = []
        for log in logs:
            log.total_time = user_log_times.get(log.user, timedelta())
            logs_with_total_time.append(log)

        return render(request, 'view_logs.html', {
            'logs': logs_with_total_time,
            'is_admin': True
        })
    else:
        logs = UserLog.objects.filter(user=request.user).order_by('-timestamp')

        total_time = timedelta()
        for log in logs:
            if log.duration:
                total_time += log.duration

        return render(request, 'view_logs.html', {
            'logs': logs,
            'total_time': total_time
        })


# ----------------------------
# 🔹 New Recognition System Views
# ----------------------------

@login_required
def start_basic_recognition(request):
    thread = threading.Thread(target=run_recognition)
    thread.start()
    return HttpResponse("✅ Basic Face Recognition started in a new thread.")


@login_required
def start_faiss_recognition(request):
    thread = threading.Thread(target=run_faiss_recognition)
    thread.start()
    return HttpResponse("✅ FAISS Face Recognition started in a new thread.")


# ----------------------------
# 🔹 Webcam Feed and Recognition
# ----------------------------

# View to handle video feed from the camera
@login_required
def video_feed(request):
    # Open the camera (0 is the default camera)
    cap = cv2.VideoCapture(0)

    def generate():
        while True:
            ret, frame = cap.read()  # Capture frame from webcam
            if not ret:
                break

            # Run face recognition on the captured frame
            # Run recognition using your custom function (make sure it processes the frame)
            recognized_faces = run_recognition(frame)  # Replace with your recognition function

            # You can now return the frame with recognition (bounding boxes, etc.)
            for (x, y, w, h) in recognized_faces:  # Example of recognized face coordinates
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Convert the frame to JPEG for web transmission
            _, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace; boundary=frame')
