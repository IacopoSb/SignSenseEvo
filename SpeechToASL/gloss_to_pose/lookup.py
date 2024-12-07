import os
import csv
import math
from concurrent.futures import ThreadPoolExecutor
from typing import List
#############################
from pose_format import Pose
from .fingerspelling_lookup import FingerspellingPoseLookup


class PoseLookup:
    
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

    def __init__(self, lookup_dir="./SpeechToASL/lexicon", fingerspelling_dir="./SpeechToASL/fingerspelling_lexicon"):
        self.fingerspelling_lookup = FingerspellingPoseLookup(directory=fingerspelling_dir)
        
        if lookup_dir is None:
            raise ValueError("Can't access pose files without specifying a directory")
        self.directory = lookup_dir
        
        csv_path = os.path.join(lookup_dir, 'index.csv')
        
        if not os.path.exists(csv_path):
            raise ValueError("Can't find index.csv file")
        
        with open(csv_path, mode='r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.dictionary = self.make_dictionary_index(rows, based_on="word")

    def read_pose(self, filename: str):
        pose_path = os.path.join(self.directory, filename)
        with open(pose_path, "rb") as f:
            return Pose.read(f.read())

    def get_pose(self, row):
        pose = self.read_pose(row["filename"])
        #print("Header:", pose.header)
        #print("Pose:", pose.body)
        #print("Data:", pose.body.data)
        #Filtrare per header e body le informazioni sulla faccia
        start_frame = math.floor(row["start"] // (1000 / pose.body.fps))
        end_frame = math.ceil(row["end"] // (1000 / pose.body.fps)) if row["end"] > 0 else -1

        return Pose(pose.header, pose.body[start_frame:end_frame])

    def lookup(self, word: str) -> Pose:
        if word in self.dictionary:
            pose = self.get_pose(self.dictionary[word])
            return word, pose
        else:
            print(f"Word '{word}' not found in lookup")
            return self.fingerspelling_lookup.lookup(word)

    def lookup_sequence(self, text: str):
        words = text.lower().split()

        def lookup_term(word):
            try:
                return self.lookup(word)
            except FileNotFoundError as e:
                print(e)
                return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lookup_term, words))

        return results
