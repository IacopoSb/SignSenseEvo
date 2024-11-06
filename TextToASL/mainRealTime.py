import argparse
import os
import time
import unicodedata
import speech_recognition as sr
import queue
import threading
import cv2
import numpy as np
from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from gloss_to_pose.fingerspelling_lookup import FingerspellingPoseLookup
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer

def remove_accents(text):
    """Rimuove accenti da lettere accentate nel testo."""
    # Normalizza il testo per separare accenti dai caratteri di base
    normalized_text = unicodedata.normalize('NFD', text)
    # Elimina i caratteri di combinazione (accenni) lasciando solo le lettere di base
    return ''.join(char for char in normalized_text if unicodedata.category(char) != 'Mn')

def _text_to_pose(text: str, fingerspelling: bool = True) -> Pose:
    """Converte un testo in una pose utilizzando il gloss specificato."""
    if fingerspelling:
        fingerspelling_lookup = FingerspellingPoseLookup()
        poses = fingerspelling_lookup.lookup_sequence(text)
    else:
        pose_lookup = PoseLookup()
        poses = pose_lookup.lookup_sequence(text)
    pose = concatenate_poses(poses)
    return pose

def recognize_speech_from_microphone(online: bool = True):
    """Riconosce il parlato dalla microfono e lo restituisce come testo."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Calibrating...")
        recognizer.adjust_for_ambient_noise(source)

    while True:
        with mic as source:
            print("Listening...")
            audio = recognizer.listen(source)
        try:
            if online:
                text = recognizer.recognize_google(audio, language="it-IT")
            else:
                text = recognizer.recognize_sphinx(audio, language="it-IT")

            text_no_accents = remove_accents(text)
            yield text_no_accents
        except sr.UnknownValueError:
            print("Could not understand audio")
            continue
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            continue

def getGIF(text):
    """Restituisce la visualizzazione della pose come una GIF."""
    concatenated_pose = _text_to_pose(text)
    pose_visual = PoseVisualizer(concatenated_pose, thickness=4)
    return pose_visual

def pose_worker(queue, stop_event):
    """Thread che gestisce la generazione di pose da testo riconosciuto."""
    for recognized_text in recognize_speech_from_microphone():
        if stop_event.is_set():
            break
        if recognized_text:
            print("Analyzing...")
            start = time.time()
            p = getGIF(recognized_text)
            print(f"GetGIF took {time.time() - start} seconds")
            start = time.time()
            for frame in p.draw():
                if stop_event.is_set():
                    break
                frame_resized = cv2.resize(np.array(frame, dtype=np.uint8), (240, 240))
                queue.put(frame_resized)
            print(f"DrawToQueue took {time.time() - start} seconds")

def display_worker(queue, stop_event, fps):
    """Thread che gestisce la visualizzazione delle immagini dalla coda con controllo degli FPS."""
    frame_interval = 1/fps
    while True:
        try:
            frame = queue.get()  # Attendi un frame
            if frame is not None:
                cv2.imshow("Pose Stream", frame)
                if cv2.waitKey(int(frame_interval * 1000)) & 0xFF == ord('q'):
                    stop_event.set()  # Imposta l'evento di stop per terminare entrambi i thread
                    break
        except queue.Empty:
            continue
    cv2.destroyAllWindows()

if __name__ == "__main__":
    frame_queue = queue.Queue()
    stop_event = threading.Event()  # Evento per segnalare lo stop

    pose_thread = threading.Thread(target=pose_worker, args=(frame_queue, stop_event))
    display_thread = threading.Thread(target=display_worker, args=(frame_queue, stop_event, 35))

    pose_thread.start()
    display_thread.start()

    pose_thread.join()
    display_thread.join()

