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

    def __init__(self, directory: str = "./fingerspelling_lexicon"):
        if directory is None:
            raise ValueError("Can't access pose files without specifying a directory")
        self.directory = directory
        csv_path = os.path.join(directory, 'index.csv')

        if not os.path.exists(csv_path):
            raise ValueError("Can't find index.csv file")
        
        with open(csv_path, mode='r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.dictionary = self.make_dictionary_index(rows, based_on="word")
        #print("Dictionary: ", self.dictionary)
        self.alphabet = sorted(self.dictionary.keys(), key=len, reverse=True)
        #print("Alfabets: ", self.alphabet)
        
    # Metodo per leggere un file di pose
    def read_pose(self, filename: str):
        pose_path = os.path.join(self.directory, filename)
        with open(pose_path, "rb") as f:
            return Pose.read(f.read())
        
    def get_pose(self, row):
        pose = self.read_pose(row['filename'])
        #print("Header:", pose.header)
        #print("Pose:", pose.body)
        #print("Data:", pose.body.data)
        #Filtrare per header e body le informazioni sulla faccia
        start_frame = math.floor(row["start"] // (1000 / pose.body.fps))
        end_frame = math.ceil(row["end"] // (1000 / pose.body.fps)) if row["end"] > 0 else -1

        return Pose(pose.header, pose.body[start_frame:end_frame])
    
    def characters_lookup(self, word: str):
        results = []
        current_index = 0

        while current_index < len(word):
            found = False 
            for key in self.alphabet:
                if word[current_index:].startswith(key):
                    results.append(self.get_pose(self.dictionary[key]))
                    current_index += len(key)
                    found = True
                    break
            if not found:
                raise FileNotFoundError(f"Characters {word} not found in fingerspelling lexicon")

        return results

    def lookup(self, word: str) -> Pose:
        word = word.lower()
        print("Word:", word)

        poses_char = list(self.characters_lookup(word))

        pose = concatenate_poses(poses_char)

        return pose

    def lookup_sequence(self, text: str):
        words = text.split()
        
        def lookup_term(word):
            try:
                return self.lookup(word)
            except FileNotFoundError as e:
                print(e)
                return None
        
        with ThreadPoolExecutor() as executor:
            results = executor.map(lookup_term, words)
        
        poses = [result for result in results if result is not None]
        
        if len(poses) == 0:
            raise Exception(f"No poses found for terms in: {text}")

        return poses