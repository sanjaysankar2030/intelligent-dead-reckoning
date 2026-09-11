"""
Script to train the Forward Velocity ML model on synthetic data.
Ensures deterministic seeds, train/validation split, and saves the model.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models.dataset_generator import SyntheticTrajectoryGenerator
from core.models.velocity_estimator import Velocity1DCNN

class IMUWindowDataset(Dataset):
    def __init__(self, data, window_size=100):
        self.samples = []
        for traj in data:
            acc = traj['accel_v']
            gyr = traj['gyro_v']
            vel = traj['vel_v']
            
            N = len(acc)
            for i in range(0, N - window_size, 10):
                window_acc = acc[i:i+window_size].T # (3, W)
                window_gyr = gyr[i:i+window_size].T # (3, W)
                
                feat = np.vstack([window_acc, window_gyr]).astype(np.float32) # (6, W)
                
                # Target is the forward velocity at the center or end of window
                # Let's use the end of the window
                target_vel = np.float32(vel[i+window_size-1, 0])
                
                self.samples.append((feat, target_vel))
                
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        return self.samples[idx]

def gaussian_nll_loss(pred, log_var, target):
    """Negative log likelihood for Gaussian uncertainty prediction."""
    var = torch.exp(log_var)
    loss = 0.5 * ((pred - target)**2 / var + log_var)
    return loss.mean()

def train(epochs: int = 10, save_path: str = "velocity_model.pth"):
    torch.manual_seed(42)
    np.random.seed(42)
    
    gen = SyntheticTrajectoryGenerator(seed=42)
    print("Generating dataset...")
    # Generate 50 trajectories for train, 10 for validation
    train_data = gen.generate_random_dataset(num_trajectories=50, length_sec=10.0)
    val_data = gen.generate_random_dataset(num_trajectories=10, length_sec=10.0)
    
    train_dataset = IMUWindowDataset(train_data)
    val_dataset = IMUWindowDataset(val_data)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    model = Velocity1DCNN()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    print("Training...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            vel, log_var = model(x)
            loss = gaussian_nll_loss(vel, log_var, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        # Validation
        model.eval()
        val_loss = 0.0
        val_rmse = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                vel, log_var = model(x)
                loss = gaussian_nll_loss(vel, log_var, y)
                val_loss += loss.item()
                val_rmse += torch.mean((vel - y)**2).item()
                
        train_loss /= len(train_loader)
        val_loss /= len(val_loader)
        val_rmse = np.sqrt(val_rmse / len(val_loader))
        
        print(f"Epoch {epoch+1}/{epochs} | Train NLL: {train_loss:.4f} | Val NLL: {val_loss:.4f} | Val RMSE: {val_rmse:.4f} m/s")
        
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

if __name__ == "__main__":
    train()
