import argparse

from gloss_to_pose.concatenate import concatenate_poses
from gloss_to_pose.lookup import PoseLookup
from gloss_to_pose.fingerspelling_lookup import FingerspellingPoseLookup

#####################################################
from pose_format import Pose
from gloss_to_pose.pose_visualizer import PoseVisualizer


def text_to_pose(text: str, directory: str, fingerspelling: bool = False) -> Pose:
    if(fingerspelling):
        fingerspelling_lookup = FingerspellingPoseLookup(directory)
        poses = fingerspelling_lookup.lookup_sequence(text)
    else:
        pose_lookup = PoseLookup(directory)
        poses = pose_lookup.lookup_sequence(text)
    pose = concatenate_poses(poses)
    return pose

if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()

    args_parser.add_argument("--text", type=str, required=True)
    args_parser.add_argument("--directory", type=str, required=True)
    args_parser.add_argument("--pose", type=str, required=True)

    args = args_parser.parse_args()

    pose = text_to_pose(args.text, args.directory)

    with open(args.pose, "wb") as f:
        pose.write(f)

    with open(args.pose, "rb") as f:
        p = Pose.read(f.read())

    scale = p.header.dimensions.width / 256
    p.header.dimensions.width = int(p.header.dimensions.width / scale)
    p.header.dimensions.height = int(p.header.dimensions.height / scale)
    p.body.data = p.body.data / scale

    v = PoseVisualizer(p, thickness=4)

    v.save_gif(args.pose+".gif", v.draw())

