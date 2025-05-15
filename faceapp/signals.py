from django.db.models.signals import pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils.timezone import now
from .models import FaceData, UserLog
from PIL import Image
import numpy as np
import insightface
import pickle

# Initialize face recognition model
model = insightface.app.FaceAnalysis()
model.prepare(ctx_id=0, det_size=(640, 640))

# In-memory dictionary to store login timestamps
login_times = {}

@receiver(pre_save, sender=FaceData)
def generate_embedding(sender, instance, **kwargs):
    if instance.image and not instance.embedding:
        img = Image.open(instance.image)
        img = np.array(img)

        faces = model.get(img)
        if faces:
            embedding = faces[0].embedding
            instance.embedding = pickle.dumps(embedding)

@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    # Store the login time in the dictionary
    login_times[user.id] = now()
    UserLog.objects.create(user=user, action="Logged in")

@receiver(user_logged_out)
def handle_user_logout(sender, request, user, **kwargs):
    login_time = login_times.pop(user.id, None)
    if login_time:
        duration = now() - login_time
        # Store the logout action along with the duration
        UserLog.objects.create(user=user, action="Logged out", duration=duration)
    else:
        UserLog.objects.create(user=user, action="Logged out")
