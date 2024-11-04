import argparse
import speech_recognition as sr
import time
from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from gloss_to_pose.fingerspelling_lookup import FingerspellingPoseLookup
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer
import matplotlib.pyplot as plt

def _text_to_pose(text: str, directory: str, fingerspelling: bool = True) -> Pose:
    if fingerspelling:
        fingerspelling_lookup = FingerspellingPoseLookup(directory)
        poses = fingerspelling_lookup.lookup_sequence(text)
    else:
        pose_lookup = PoseLookup(directory)
        poses = pose_lookup.lookup_sequence(text)
    pose = concatenate_poses(poses)
    return pose

def recognize_speech_from_microphone():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    silence_duration = 3  # Durata in secondi per considerare l'assenza di parole
    last_speech_time = time.time()

    while True:
        with mic as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            last_speech_time = time.time()  # Aggiorna il tempo dell'ultima parola
            yield text  # Restituisci il testo riconosciuto
        except sr.UnknownValueError:
            continue  # Ignora se non riesce a riconoscere il parlato
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            continue

        # Controlla se ci sono stati 3 secondi di silenzio
        if time.time() - last_speech_time > silence_duration:
            print("No speech detected for 3 seconds. Processing...")
            break

def update_visualization(poses, directory):
    # Converte direttamente da testo a pose
    concatenated_pose = _text_to_pose(' '.join(poses), directory)
    
    # Visualizza in tempo reale
    with plt.ioff():  # Disattiva il blocco di Matplotlib
        plt.clf()  # Pulisce la figura
        v = PoseVisualizer(concatenated_pose, thickness=4)

        # Disegna la visualizzazione
        v.draw()
        plt.axis('off')  # Nasconde gli assi
        plt.pause(0.1)  # Mantiene la visualizzazione aperta brevemente

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=str, required=True)
    args = parser.parse_args()

    plt.ion()  # Attiva la modalità interattiva per la visualizzazione
    
    poses = []  # Lista per memorizzare le pose riconosciute
    for recognized_text in recognize_speech_from_microphone():
        poses.append(recognized_text)
        update_visualization(poses, args.directory)

    plt.show()  # Mostra la figura finale
