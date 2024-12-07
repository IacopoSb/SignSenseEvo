import csv
import math
import os
from pathlib import Path
from typing import List
from pose_format import Pose
from .concatenate import concatenate_poses
from concurrent.futures import ThreadPoolExecutor

class FingerspellingPoseLookup():
    def make_dictionary_index(self, rows: List, based_on: str):
        dictionary = {}
        for d in rows:
            term = d[based_on].lower()
            dictionary[term] = {
                "filename": d['filename'],
                "word": d[based_on],
                "start": int(d['start']),
                "end": int(d['end'])
            }
        return dictionary

    def __init__(self, directory: str = "./SpeechToASL/fingerspelling_lexicon"):
        if directory is None:
            raise ValueError("Can't access pose files without specifying a directory")
        self.directory = directory

        csv_path = os.path.join(directory, 'index.csv')

        if not os.path.exists(csv_path):
            raise ValueError("Can't find index.csv file")
        
        with open(csv_path, mode='r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.dictionary = self.make_dictionary_index(rows, based_on="word")
        self.alphabet = sorted(self.dictionary.keys(), key=len, reverse=True)
        
    # Metodo per leggere un file di pose
    def read_pose(self, filename: str):
        pose_path = os.path.join(self.directory, filename)
        with open(pose_path, "rb") as f:
            return Pose.read(f.read())
        
    def get_pose(self, row):
        pose = self.read_pose(row['filename'])
        start_frame = math.floor(row["start"] // (1000 / pose.body.fps))
        end_frame = math.ceil(row["end"] // (1000 / pose.body.fps)) if row["end"] > 0 else -1
        return Pose(pose.header, pose.body[start_frame:end_frame])
    
    def characters_lookup(self, letter: str):
        if letter in self.dictionary:
            return self.get_pose(self.dictionary[letter])
        else:
            raise FileNotFoundError(f"Character {letter} not found in fingerspelling lexicon")

    def lookup(self, word: str):
        word = word.lower()
        
        def lookup_letter(letter):
            try:
                return self.characters_lookup(letter)
            except FileNotFoundError as e:
                print(e)
                return None
        
        with ThreadPoolExecutor() as executor:
            poses = list(executor.map(lookup_letter, word))
        
        return word, concatenate_poses(poses)
