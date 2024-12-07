import time
import unicodedata
from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer
import numpy as np
import cv2

def text_to_pose(text: str, dir: str, dir_fingerspelling: str):
    print("LOOKUP...")
    start = time.time()

    poseLookup = PoseLookup(lookup_dir=dir, fingerspelling_dir=dir_fingerspelling)
    words_poses = poseLookup.lookup_sequence(text)
    words, poses = zip(*words_poses)

    print(f"Lookup took {time.time() - start:.2f} seconds")
    
    print("CONCATENATE...")
    start = time.time()

    pose = concatenate_poses(poses)
    
    print(f"Concatenation took {time.time() - start:.2f} seconds")
    return pose

def parse_text(text):
    # Normalizza e Rimuove accenti
    normalized_text = unicodedata.normalize('NFD', text)
    # Filtra solo caratteri tra 'a' e 'z' senza accenti, mantenendo gli spazi
    return ''.join(
        char for char in normalized_text 
        if unicodedata.category(char) != 'Mn' and ('a' <= char.lower() <= 'z' or char == ' ')
    ).lower()

def text_to_frames(text: str, lexiconPath: str, fingerspellingLexiconPath: str, target_size: int = 720):
    print("Generating pose for text...")
    start = time.time()

    text_parsed = parse_text(text)
    concatenated_pose = text_to_pose(text_parsed, lexiconPath, fingerspellingLexiconPath)
    p = PoseVisualizer(concatenated_pose, thickness=4)
   
    png_frames = []
    for frame in p.draw():
        resized_frame = cv2.resize(frame, (target_size, target_size))
        
        #ret, buffer = cv2.imencode('.png', resized_frame)

        png_frames.append(resized_frame.tobytes())  # Convert the frame to bytes and append to the list
    
    print(f"Total Pose generation took {time.time() - start:.2f} seconds")

    print("Shape of the frames: ", resized_frame.shape)
    print("FPS: ", concatenated_pose.body.fps)
    return png_frames