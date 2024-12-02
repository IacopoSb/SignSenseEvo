import argparse
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

    print("Words: ", words)

    print(f"Lookup took {time.time() - start:.2f} seconds")
    print("CONCATENATE...")
    start = time.time()

    pose = concatenate_poses(poses)
    
    print(f"Concatenation took {time.time() - start:.2f} seconds")
    return pose

def recognize_speech_from_microphone(stop_event, ONLINE: bool = True):
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
            audio = recognizer.listen(source, phrase_time_limit=10)

        try:
            if ONLINE:
                text = recognizer.recognize_google(audio, language="it-IT")
            else:
                # Offline recognition (Database it-IT required)
                text = recognizer.recognize_sphinx(audio, language="it-IT")

            print("Recognized text:", text)

            if text != "":
                text = "Buongiorno, oggi vi presento SignSenseEvo"
                #text = "Ciao come stai oggi? Io bene grazie."
                text_parsed = parse_text(text)
                text_parsed = "buongiorno oggi vi presento SignSenseEvo"
                #text_parsed = "ciao comestai oggi io bene grazie"
                print("Parsed text:", text_parsed)
                yield (text, text_parsed)

        except sr.UnknownValueError:
            print("Could not understand audio")
            continue
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            continue

def frame_worker(frame_queue, stop_event, target_size):
    for recognized_text, parsed_text in recognize_speech_from_microphone(stop_event):
        
        if stop_event.is_set():
            break

        print("Generating pose for recognized text...")
        start = time.time()
        
        concatenated_pose = text_to_pose(parsed_text)
        p = PoseVisualizer(concatenated_pose, thickness=4)

        for frame in p.draw():
            if stop_event.is_set():
                break
            frame_resized = cv2.resize(np.array(frame, dtype=np.uint8), (target_size, target_size))
            frame_queue.put((frame_resized, recognized_text))
        
        print(f"Total Pose generation took {time.time() - start:.2f} seconds")

def processing_text_to_display(text, max_width, font_scale, thickness):
    accent_map = {
        'à': "a'", 'á': "a'", 'è': "e'", 'é': "e'", 
        'ì': "i'", 'í': "i'", 'ò': "o'", 'ó': "o'",
        'ù': "u'", 'ú': "u'",
    }
    text = ''.join(accent_map.get(c, c) for c in text)
    ######################################################
    lines = []
    current_line = ""
    for word in text.split():
        test_line = f"{current_line} {word}".strip()
        text_size = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_COMPLEX, fontScale=font_scale, thickness=thickness)[0]
        if text_size[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines

def drawLines(frame, lines, font_scale=1, thickness=1):
    y = 100  # Posizione iniziale y
    for line in lines:
        text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_COMPLEX, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        cv2.putText(frame, line, (text_x, y), cv2.FONT_HERSHEY_COMPLEX, fontScale=font_scale, color=(0, 0, 0), thickness=thickness, lineType=cv2.LINE_AA)
        y += text_size[1] + 5  # Spazio tra le righe

def display_worker(frame_queue, 
                   stop_event, frame_size, 
                   h_screen_size, v_screen_size,
                    font_scale, thickness, fps=35):
    frame_interval = 1 / fps
    frame_white = np.ones((frame_size, frame_size, 3), dtype=np.uint8) * 255
    text_white = "Listening..."

    horizontal_border = max((h_screen_size - frame_size) // 2, 0)
    vertical_border = max((v_screen_size - frame_size) // 2, 0)

    # Imposta la finestra in modalità full screen
    cv2.namedWindow("Pose Stream", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Pose Stream", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        key = cv2.waitKey(int(frame_interval * 1000)) & 0xFF
        if key == ord('q'):
            stop_event.set()
            break
        elif key == ord('w'):
            # Svuota il buffer dei frame
            with frame_queue.mutex:
                frame_queue.queue.clear()
            print("Frame buffer cleared.")

        if frame_queue.empty():
            frame, text = frame_white.copy(), text_white
        else:
            frame, text = frame_queue.get()

        # Aggiungi bordi calcolati per centrare l'immagine nello schermo
        frame_with_borders = cv2.copyMakeBorder(
            frame, vertical_border, vertical_border, horizontal_border, horizontal_border,
            cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )

        lines = processing_text_to_display(text, frame_with_borders.shape[0] - 10, font_scale, thickness)
        drawLines(frame_with_borders, lines, font_scale, thickness)

        cv2.imshow("Pose Stream", frame_with_borders)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parameters")
    
    parser.add_argument("--fps", type=int, default=40, 
                        help="Frame rate per il display")
    parser.add_argument("--frame_square_size", type=int, default=720, 
                        help="Dimensione quadrata del frame")
    parser.add_argument("--h_screen_size", type=int, default=1920, 
                        help="Larghezza dello schermo")
    parser.add_argument("--v_screen_size", type=int, default=1080, 
                        help="Altezza dello schermo")
    parser.add_argument("--font_scale", type=int, default=3, 
                        help="Scala del font")
    parser.add_argument("--thickness", type=int, default=3, 
                        help="Spessore del testo")
    
    args = parser.parse_args()
    
    frame_queue = queue.Queue()
    stop_event = threading.Event()

    frame_thread = threading.Thread(target=frame_worker, 
                                    args=(frame_queue, stop_event, args.frame_square_size))
    display_thread = threading.Thread(target=display_worker, 
                                      args=(frame_queue, stop_event, 
                                            args.frame_square_size, 
                                            args.h_screen_size, args.v_screen_size,
                                            args.font_scale, args.thickness, args.fps))

    frame_thread.start()
    display_thread.start()

    frame_thread.join()
    display_thread.join()

#  python .\SpeechToASL\mainRealTime.py --fps 40 --frame_square_size 720 --h_screen_size 1920 --v_screen_size 1080 --font_scale 3 --thickness 3