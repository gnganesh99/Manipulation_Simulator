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



@torch.no_grad()
def sample_next_state(s, a, delta_norm = None):

    model_path = "./models/single_gaussian_model3.pt"
    model = torch.jit.load(model_path)
    model.eval()

    #a = np.random.uniform(-1, 1, size=(s.shape[0], 2))  # Sample random actions
    
    s = torch.as_tensor(s, dtype=torch.float32)
    a = torch.as_tensor(a, dtype=torch.float32)

    mu, std, _ = model(s, a)        # delta distribution
    eps = torch.randn_like(std)
    delta = mu + std * eps

    if delta_norm is not None:
        delta = delta_norm.denormalize(delta)


    #ns = s + delta
    if s.dim() == 1:
        tt = torch.concatenate([s[-2:], s[ -2:]], dim=-1)  # Contacatenate the targets
    else:
        tt = torch.concatenate([s[:, -2:], s[:, -2:]], dim=-1)  # Contacatenate the targets
    ns = delta + tt
    
    ns = ns.cpu().numpy()
    return ns