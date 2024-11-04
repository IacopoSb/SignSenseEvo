import argparse

from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from gloss_to_pose.fingerspelling_lookup import FingerspellingPoseLookup

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
#####################################################
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer


def _text_to_pose(text: str, directory: str, fingerspelling: bool = True) -> Pose:
    if(fingerspelling):
        fingerspelling_lookup = FingerspellingPoseLookup(directory)
        poses = fingerspelling_lookup.lookup_sequence(text)
    else:
        pose_lookup = PoseLookup(directory)
        poses = pose_lookup.lookup_sequence(text)
    pose = concatenate_poses(poses)
    return pose

def _text_input_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--text", type=str, required=True)
    parser.add_argument("--directory", type=str, required=True)
    parser.add_argument("--pose", type=str, required=True)

if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    _text_input_arguments(args_parser)
    args = args_parser.parse_args()

    # Converte direttamente da testo a pose
    pose = _text_to_pose(args.text, args.directory)

    # Salva la pose nel file di output specificato
    with open(args.pose, "wb") as f:
        pose.write(f)

    with open(args.pose, "rb") as f:
        p = Pose.read(f.read())

    # Resize to 256, for visualization speed
    scale = p.header.dimensions.width / 256
    p.header.dimensions.width = int(p.header.dimensions.width / scale)
    p.header.dimensions.height = int(p.header.dimensions.height / scale)
    p.body.data = p.body.data / scale

    # Genearate .gif
    v = PoseVisualizer(p, thickness=4)

    v.save_gif(args.pose+".gif", v.draw())

