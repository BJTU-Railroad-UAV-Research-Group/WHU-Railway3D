from sklearn.neighbors import KDTree
from os.path import join, exists, dirname, abspath
import numpy as np
import os, glob, pickle
import sys

BASE_DIR = dirname(abspath(__file__))
ROOT_DIR = dirname(BASE_DIR)
sys.path.append(BASE_DIR)
sys.path.append(ROOT_DIR)
from helper_ply import read_ply, write_ply
from helper_tool import DataProcessing as DP
from helper_tool import ConfigEnv as cfg

def read_file_paths(file_path):
    with open(file_path, 'r') as file:
        paths = file.readlines()
    paths = [path.rstrip() for path in paths]
    return paths

def add_prefix(paths, prefix):
    return [prefix + path for path in paths]

def split_filename(paths):
    return [path.split('/')[-1][:-4] for path in paths]

prefix = '/data1/mengfanteng/dataset/ENVPC_dataset/20241129_MYEnv_PC/'
dataset_path = '/data1/mengfanteng/dataset/ENVPC_dataset/RandLANet-format/'
train_file_path_txt = 'repos/filelist/env/train.txt'
val_file_path_txt   = 'repos/filelist/env/val.txt'

sub_pc_folder = join(dirname(dataset_path), 'input_{:.3f}'.format(cfg.sub_grid_size))
os.makedirs(sub_pc_folder, exist_ok=True)# os.mkdir(sub_pc_folder) if not exists(sub_pc_folder) else None

train_paths = read_file_paths(train_file_path_txt)
val_paths = read_file_paths(val_file_path_txt)

train_files = add_prefix(train_paths, prefix)
val_files = add_prefix(val_paths, prefix)
all_filespath = train_files + val_files

train_file_name = split_filename(train_paths)
val_file_name = split_filename(val_paths)
all_file_name = train_file_name + val_file_name

railway3d_label_to_color = np.asarray([
    [154,107,56]   ,
    [160,112,160]  ,
    [251,143,49]   ,
    [62,170,163]   ,
    [229,202,63]   ,
    [101,101,206]  ,
    [180,47,174]   ,
    [166,255,64]   ,
    [253,51,103]   ,
    [154,194,231]  ,
    [218,219,220]
])

for pc_path in all_filespath:
    print('dealing with : ',pc_path)
    file_name=os.path.basename(pc_path)[:-4]

    # check if it has already calculated
    if exists(join(sub_pc_folder, file_name + '_KDTree.pkl')):
        continue

    # Load pointcloud file
    data = read_ply(pc_path)
    xyz = np.vstack((data['x'], data['y'], data['z'])).T

    labels = data['scalar_Scalar_field_#8']
    labels = labels.reshape(np.size(labels, 0), 1)
    labels = labels.astype(np.uint8)

    intensity = np.vstack((data['red'], data['green'], data['blue'])).T
    intensity = intensity.astype(np.float32)
    print('original_intensity.max = ', intensity.max())
    intensity[intensity > 255] = 255
    print('new_intensity.max = ', intensity.max())
    intensity = intensity.astype(np.float32)

    sub_xyz, sub_intensity, sub_labels = DP.grid_sub_sampling(xyz.astype(np.float32), intensity, labels, cfg.sub_grid_size)
    sub_xyz = sub_xyz.astype(np.double)
    sub_labels = np.squeeze(sub_labels)
    sub_intensity = sub_intensity / 255

    sub_ply_file = join(sub_pc_folder, file_name + '.ply')
    write_ply(sub_ply_file, 
             [sub_xyz.astype(np.float64), sub_intensity[:,0].astype(np.float64), sub_intensity[:,1].astype(np.float64),sub_intensity[:,2].astype(np.float64), sub_labels.astype(np.uint8)], 
             ['x', 'y', 'z', 'intensity_r','intensity_g','intensity_b', 'class'])

    search_tree = KDTree(sub_xyz, leaf_size=10)
    kd_tree_file = join(sub_pc_folder, file_name + '_KDTree.pkl')
    with open(kd_tree_file, 'wb') as f:
        pickle.dump(search_tree, f)

    proj_idx = np.squeeze(search_tree.query(xyz.astype(np.float32), return_distance=False))
    proj_idx = proj_idx.astype(np.int32)
    proj_save = join(sub_pc_folder, file_name + '_proj.pkl')
    with open(proj_save, 'wb') as f:
        pickle.dump([proj_idx, labels], f)
