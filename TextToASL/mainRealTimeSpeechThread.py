import time
import unicodedata
import speech_recognition as sr
import queue
import threading
import cv2
import numpy as np

from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer

def parse_text(text):
    # Normalizza e Rimuove accenti
    normalized_text = unicodedata.normalize('NFD', text)
    # Filtra solo caratteri tra 'a' e 'z' senza accenti, mantenendo gli spazi
    return ''.join(
        char for char in normalized_text 
        if unicodedata.category(char) != 'Mn' and ('a' <= char.lower() <= 'z' or char == ' ')
    ).lower()

def text_to_pose(text: str) -> Pose:
    print("LOOKUP...")
    start = time.time()

    poseLookup = PoseLookup()
    words_poses = poseLookup.lookup_sequence(text)
    words, poses = zip(*words_poses)

    print(f"Lookup took {time.time() - start:.2f} seconds")
    print("CONCATENATE...")
    start = time.time()

    pose = concatenate_poses(poses)
    
    print(f"Concatenation took {time.time() - start:.2f} seconds")
    return pose

def speech_worker(speech_queue, stop_event, ONLINE=False):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("Calibrating...")
        recognizer.adjust_for_ambient_noise(source)
        
    while True:
        
        if stop_event.is_set():
            break

        with mic as source:
            print("Listening...")
            audio = recognizer.listen(source)
        try:
            if ONLINE:
                text = recognizer.recognize_google(audio, language="it-IT")
            else:
                text = recognizer.recognize_sphinx(audio, language="it-IT")
                        
            if text != "":
                text_parsed = parse_text(text)
                print("Recognized text:", text_parsed)
                speech_queue.put(text_parsed)

        except sr.UnknownValueError:
            print("Could not understand audio")
            continue
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            continue
 

def frame_worker(speech_queue, frame_queue, stop_event, target_size=(240, 240)):
    while True:

        if stop_event.is_set():
            break
        if speech_queue.empty():
            continue

        recognized_text = speech_queue.get()

        print("Generating pose for recognized text...")
        start = time.time()

        pose = text_to_pose(recognized_text)

        pose_visual = PoseVisualizer(pose, thickness=4)
        for frame in pose_visual.draw():
            if stop_event.is_set():
                break
            frame_resized = cv2.resize(np.array(frame, dtype=np.uint8), target_size)
            frame_queue.put(frame_resized)

        print(f"Total Pose generation took {time.time() - start:.2f} seconds")


def display_worker(frame_queue, stop_event, fps = 35, target_size=(240, 240)):
    frame_interval = 1 / fps
    frame_white = np.ones((target_size[1], target_size[0], 3), dtype=np.uint8) * 255
    
    while True:

        if cv2.waitKey(int(frame_interval * 1000)) & 0xFF == ord('q'):
            stop_event.set()
            break

        if frame_queue.empty():
            frame = frame_white
        else:
            frame = frame_queue.get()
        
        if frame is not None:
            cv2.imshow("Pose Stream", frame)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    speech_queue = queue.Queue()
    frame_queue = queue.Queue()
    stop_event = threading.Event()

    speech_thread = threading.Thread(target=speech_worker, args=(speech_queue, stop_event))
    frame_thread = threading.Thread(target=frame_worker, args=(speech_queue, frame_queue, stop_event))
    display_thread = threading.Thread(target=display_worker, args=(frame_queue, stop_event))

    speech_thread.start()
    frame_thread.start()
    display_thread.start()

    speech_thread.join()
    frame_thread.join()
    display_thread.join()
