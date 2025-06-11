import cv2
import threading

class VideoStream:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        self.ret, self.frame = self.cap.read()
        self.lock = threading.Lock()
        self.stopped = False

        thread = threading.Thread(target=self.update, args=())
        thread.daemon = True
        thread.start()

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret = ret
                self.frame = frame

    def read(self):
        with self.lock:
            return self.ret, self.frame.copy() if self.frame is not None else (False, None)

    def stop(self):
        self.stopped = True
        self.cap.release()
