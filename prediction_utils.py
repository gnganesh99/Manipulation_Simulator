import numpy as np
import torch
import json
from collision_detection import get_collision_indices, get_first_collision_point
import random

model_path = "./models/gmm_model0.pt"
meta_path = "./models/gmm_model0_meta.json"

_STATE_DICT_CACHE = {}
_META_CACHE = {}




def get_next_state(state, target, action, mode="ideal", all_positions=None, object_radius=12):
    mode = str(mode).strip().lower()

    state = np.asarray(state, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    action = np.asarray(action, dtype=np.float32)

    model_state = np.concatenate([state, target], axis=-1)

    # Normalize slider actions from [10, 90] into [-1, 1] and append a fixed offset.
    action = ((action - 10.0) / 80.0) * 2.0 - 1.0
    offset = np.zeros((action.shape[0], 2), dtype=np.float32)
    model_action = np.concatenate([action, offset], axis=-1)

    state_tensor = torch.as_tensor(model_state, dtype=torch.float32).clip(0, 1)
    action_tensor = torch.as_tensor(model_action, dtype=torch.float32).clip(-1, 1)

    if mode == "ideal":
        sigmoid_type = lambda x: 1 / (1 + np.exp(-10 * x))
        delta_s = target - state

        action0 = action_tensor[:, 0].cpu().numpy().ravel()
        action1 = action_tensor[:, 1].cpu().numpy().ravel()
        delta_factor = (1 - sigmoid_type(action0[0] - (-0.5))) * sigmoid_type(action1[0] - 0.5)
        next_state = state + delta_s * delta_factor
        
    else:

        next_state = sample_next_state(
            model_path=model_path,
            meta_path=meta_path,
            state_sample=state_tensor,
            action_sample=action_tensor,
            mode=mode,
        )[0]

    next_state = np.asarray(next_state, dtype=np.float32).clip(0, 1)


    if all_positions is not None and len(all_positions) > 1:
        all_positions = np.asarray(all_positions, dtype=np.float32)
        current_obj_idx  = np.where((all_positions == state).all(axis=1))[0]
        if len(current_obj_idx) > 1:
            print(f"Current object index for collision check: {current_obj_idx}")
        all_positions = np.delete(all_positions, current_obj_idx, axis=0)  # Remove the current object's position from collision checks
        object_radius = object_radius / 500  # Assuming a radius of 12 pixels for the object, normalized to [0, 1]

        collision_point = get_first_collision_point(state, next_state, all_positions, object_width=object_radius*2, padding= -0.01)
        #collision_indices = get_collision_indices(state, next_state, all_positions, object_width=object_radius*2, padding=0)

        if collision_point is not None:
            print(f"Collision detected! Original next state: {next_state}, Collision point: {collision_point}")
            next_state = np.array(collision_point, dtype=np.float32).reshape(-1, 2).clip(0, 1)
            
    return next_state



def sample_next_state(model_path, meta_path, state_sample, action_sample, mode="predictive", device=None):
    mode = str(mode).strip().lower()
    if mode not in ('ideal', 'predictive'):
        mode = 'predictive'

    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

 
    
    model_meta = load_model_meta(meta_path)
    state_dim = model_meta.get('state_dim')
    action_dim = model_meta.get('action_dim')

    assert state_sample.shape[1] == state_dim, f"Expected state dimension {state_dim}, got {state_sample.shape[1]}"
    assert action_sample.shape[1] == action_dim, f"Expected action dimension {action_dim}, got {action_sample.shape[1]}"
    

    with torch.no_grad():
        state_sample = state_sample.to(device)
        action_sample = action_sample.to(device)
        dist, delta_pred_norm = run_gmm_state_dict_inference(
            model_path=model_path,
            model_meta=model_meta,
            state_sample=state_sample,
            action_sample=action_sample,
            device=device,
        )

    delta_norm = create_delta_norm_from_meta(meta_path)

    delta_pred_norm = delta_pred_norm.cpu().numpy()
    delta_pred = delta_norm.denormalize(delta_pred_norm)
    

    state_np = state_sample.cpu().numpy()
    target_state = state_np[:, 2:4]

    
    pred_next_state = target_state + delta_pred


    

    return pred_next_state, delta_norm


def load_model_meta(meta_path):
    cached = _META_CACHE.get(meta_path)
    if cached is None:
        with open(meta_path, "r") as f:
            cached = json.load(f)
        _META_CACHE[meta_path] = cached
    return cached


def load_model_state_dict(model_path, device):
    cache_key = (model_path, str(device))
    cached = _STATE_DICT_CACHE.get(cache_key)
    if cached is None:
        raw_state = torch.load(model_path, map_location=device)
        cached = {key: value.to(device) for key, value in raw_state.items()}
        _STATE_DICT_CACHE[cache_key] = cached
    return cached


def linear(x, weight, bias):
    return x @ weight.T + bias


def run_gmm_state_dict_inference(model_path, model_meta, state_sample, action_sample, device):
    state_dict = load_model_state_dict(model_path, device)
    num_components = int(model_meta["num_components"])

    x = torch.cat([state_sample, action_sample], dim=-1)
    x = torch.relu(linear(x, state_dict["net.0.weight"], state_dict["net.0.bias"]))
    x = torch.relu(linear(x, state_dict["net.2.weight"], state_dict["net.2.bias"]))

    coeff_logits = linear(x, state_dict["coeff.weight"], state_dict["coeff.bias"])
    mixture_weights = torch.softmax(coeff_logits, dim=-1)

    mu = linear(x, state_dict["mu.weight"], state_dict["mu.bias"]).view(-1, num_components, 2)
    delta_pred_norm = (mixture_weights.unsqueeze(-1) * mu).sum(dim=1)

    return mixture_weights, delta_pred_norm


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
