import torch
import torch.nn as nn
import torch.nn.functional as F

from collections import deque
import random
import numpy as np
import os
import h5py
from sklearn.model_selection import train_test_split

from torch.utils.data import DataLoader, Dataset
import matplotlib.pyplot as plt
import h5py
import json

model_path = "./models/gmm_model0.pt"
meta_path = "./models/gmm_model0_meta.json"




def get_next_state(s, t, a, mode = 'ideal'):

    s = np.concatenate([s, t], axis=-1)  # Concatenate the targets
    a = ((a - 10) / 80 )* 2 - 1  # Normalize actions to [-1, 1]

    s = torch.as_tensor(s, dtype=torch.float32).clip(0, 1)
    a = torch.as_tensor(a, dtype=torch.float32).clip(-1, 1)

    next_state = sample_next_state(model_path, meta_path, s, a, mode = mode)[0]
    next_state = next_state.clip(0, 1)
    
    return next_state








def create_delta_norm_from_meta(meta_path):
    with open(meta_path, "r") as f:
        meta = json.load(f)

    if "delta_norm_mean" not in meta or "delta_norm_std" not in meta:
        raise KeyError(
            f"Meta file at '{meta_path}' must contain 'delta_norm_mean' and 'delta_norm_std'. "
            f"Available keys: {list(meta.keys())}"
        )

    mean = np.array(meta["delta_norm_mean"], dtype=np.float32)
    std = np.array(meta["delta_norm_std"], dtype=np.float32)

    try:
        # common signature
        delta_norm_obj = Normalizer(mean=mean, std=std)
    except TypeError:
        try:
            # fallback positional signature
            delta_norm_obj = Normalizer(mean, std)
        except TypeError:
            # last-resort fallback
            delta_norm_obj = Normalizer()
            delta_norm_obj.mean = mean
            delta_norm_obj.std = std

    return delta_norm_obj


def sample_next_state(model_path, meta_path, state_sample, action_sample, device=None, mode = 'ideal'):

    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

 
    
    with open(meta_path, 'r') as f:
        model_meta = json.load(f)
        state_dim = model_meta.get('state_dim')  # Default to 4 if not specified
        action_dim = model_meta.get('action_dim')  # Default to 2 if not specified

    assert state_sample.shape[1] == state_dim, f"Expected state dimension {state_dim}, got {state_sample.shape[1]}"
    assert action_sample.shape[1] == action_dim, f"Expected action dimension {action_dim}, got {action_sample.shape[1]}"
    

    inference_model = torch.jit.load(model_path)

    inference_model.load_state_dict(torch.load(model_path, map_location=device))
    inference_model.eval()

   

    with torch.no_grad():
        dist, delta_pred_norm = inference_model(state_sample, action_sample)

    delta_norm = create_delta_norm_from_meta(meta_path)

    delta_pred_norm = delta_pred_norm.cpu().numpy()
    delta_pred = delta_norm.denormalize(delta_pred_norm)
    

    state_np = state_sample.cpu().numpy()
    target_state = state_np[:, 2:4]

    
    pred_next_state = target_state + delta_pred


    if mode == 'ideal':
        sigmoid_type = lambda x: 1 / (1 + np.exp(-10*x))
        curr_state = state_np[:, :2]
        delta_s = target_state - curr_state

        action0 = action_sample[:, 0].cpu().numpy().ravel()
        action1 = action_sample[:, 1].cpu().numpy().ravel()
        delta_factor = (1-sigmoid_type(action0[0] - (-0.5))) * sigmoid_type(action1[0] - (0.5))  # Add sigmoid-based modulation at action
        pred_next_state = target_state + delta_s * delta_factor

    

    return pred_next_state, delta_norm



    



class Normalizer:
    def __init__(self, data = None, mean = None, std = None):
        if data is not None:
            self.mean = data.mean(axis=0)
            self.std = data.std(axis=0) + 1e-8  # avoid division by zero
        else:
            self.mean = mean
            self.std = std

    # Returns the normalized version of the input data such that it has zero mean and unit variance.
    def normalize(self, x): 
        return (x - self.mean) / self.std

    # Returns the denormalized version of the input data, which is the original data before normalization.
    def denormalize(self, x):
        return x * self.std + self.mean



# @torch.no_grad()
# def sample_next_state(s, t, a, delta_norm = None):

#     model_path = "./models/single_gaussian_model3.pt"
#     model = torch.jit.load(model_path)
#     model.eval()

#     #a = np.random.uniform(-1, 1, size=(s.shape[0], 2))  # Sample random actions
    
#     s = np.concatenate([s, t], axis=-1)  # Concatenate the targets
#     a = ((a - 10) / 80 )* 2 - 1  # Normalize actions to [-1, 1]

#     s = torch.as_tensor(s, dtype=torch.float32).clip(0, 1)
#     a = torch.as_tensor(a, dtype=torch.float32).clip(-1, 1)

#     mu, std, _ = model(s, a)        # delta distribution
#     eps = torch.randn_like(std)
#     delta = mu + std * eps

#     if delta_norm is not None:
#         delta = delta_norm.denormalize(delta)


#     #ns = s + delta
#     if s.dim() == 1:
#         tt = torch.concatenate([s[-2:], s[ -2:]], dim=-1)  # Contacatenate the targets
#     else:
#         tt = torch.concatenate([s[:, -2:], s[:, -2:]], dim=-1)  # Contacatenate the targets
#     ns = delta + tt
    
#     ns = ns.cpu().numpy().clip(0, 1)   # just check this. this has 4 dim!!!

#     return ns



# def sample_next_state1(s, t, a, delta_norm = None):

    
#     s = np.concatenate([s, t], axis=-1)  # Concatenate the targets
#     delta  = ((a - 10) / 80 )* 2 - 1  # Normalize actions to [-1, 1]

#     ns = s + delta

#     #ns = s + delta
#     if s.ndim == 1:
#         tt = np.concatenate([s[-2:], s[ -2:]], axis=-1)  # Contacatenate the targets
#     else:
#         tt = np.concatenate([s[:, -2:], s[:, -2:]], axis=-1)  # Contacatenate the targets
#     ns = delta + tt
    
#     ns = ns.cpu().numpy().clip(0, 1)

#     return ns