#import cv2
#import base64
#import json
#import asyncio
#from channels.generic.websocket import AsyncWebsocketConsumer

# Comment out the entire WebSocket consumer class
# class VideoFeedConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         # Accept the WebSocket connection
#         await self.accept()
#
#         self.streaming = True
#         self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow on Windows
#
#         # Ensure the webcam is opened successfully
#         if not self.cap.isOpened():
#             print("Failed to open webcam")
#             await self.close()  # Close the connection if webcam can't be opened
#             return
#
#         # Start the task to send video frames
#         self.task = asyncio.create_task(self.send_video_frames())
#
#     async def disconnect(self, close_code):
#         # Stop streaming and release the camera when disconnected
#         self.streaming = False
#
#         if self.cap.isOpened():
#             self.cap.release()  # Release the webcam
#         if hasattr(self, 'task'):
#             self.task.cancel()  # Cancel the task to stop sending frames
#
#     async def send_video_frames(self):
#         try:
#             while self.streaming:
#                 ret, frame = self.cap.read()
#                 if not ret:
#                     await asyncio.sleep(0.1)  # Wait a bit before trying again
#                     continue
#
#                 # Resize frame for consistency in the feed
#                 frame = cv2.resize(frame, (640, 480))
#
#                 # Encode the frame to JPEG format
#                 _, buffer = cv2.imencode('.jpg', frame)
#                 jpg_as_text = base64.b64encode(buffer).decode('utf-8')
#
#                 # Send the image data to the WebSocket
#                 await self.send(text_data=json.dumps({
#                     "image": jpg_as_text
#                 }))
#
#                 # Control the frame rate (roughly 20 FPS)
#                 await asyncio.sleep(0.05)  # ~20 FPS
#
#         except asyncio.CancelledError:
#             pass  # Handle the case where the task is cancelled
#         except Exception as e:
#             print(f"WebSocket Error: {e}")
#             await self.close()  # Close the WebSocket connection in case of error
