import numpy as np
from typing import Tuple, List, Dict

class SyntheticTrajectoryGenerator:
    """Generates synthetic 1D/2D trajectories with ground truth for ML training."""
    
    def __init__(self, dt: float = 0.01, seed: int = 42):
        self.dt = dt
        self.rng = np.random.default_rng(seed)
        
    def generate_straight_accel_decel(
        self, 
        duration: float = 10.0, 
        max_speed: float = 15.0
    ) -> Dict[str, np.ndarray]:
        """
        Generate a trajectory accelerating to max_speed, cruising, then decelerating.
        Returns:
            Dictionary containing:
            - time: (N,)
            - accel_v: (N, 3) vehicle frame acceleration
            - gyro_v: (N, 3) vehicle frame angular rate
            - vel_v: (N, 3) vehicle frame velocity
        """
        N = int(duration / self.dt)
        time = np.arange(N) * self.dt
        
        accel_x = np.zeros(N)
        vel_x = np.zeros(N)
        
        # simple profile: accelerate for 1/3, cruise 1/3, decelerate 1/3
        t1 = int(N / 3)
        t2 = int(2 * N / 3)
        
        accel_val = max_speed / (t1 * self.dt)
        
        accel_x[:t1] = accel_val
        accel_x[t1:t2] = 0.0
        accel_x[t2:] = -accel_val
        
        # Integrate to get velocity
        for i in range(1, N):
            vel_x[i] = vel_x[i-1] + accel_x[i-1] * self.dt
            
        vel_x = np.clip(vel_x, 0.0, None) # Ensure non-negative
            
        # Vehicle frame Z accel is reaction to gravity (-9.80665)
        # assuming level vehicle.
        accel_v = np.zeros((N, 3))
        accel_v[:, 0] = accel_x
        accel_v[:, 2] = -9.80665
        
        # Add some vibrational noise
        accel_v += self.rng.normal(0, 0.5, size=(N, 3))
        gyro_v = self.rng.normal(0, 0.05, size=(N, 3))
        
        vel_v = np.zeros((N, 3))
        vel_v[:, 0] = vel_x
        
        return {
            "time": time,
            "accel_v": accel_v,
            "gyro_v": gyro_v,
            "vel_v": vel_v
        }

    def generate_random_dataset(self, num_trajectories: int = 100, length_sec: float = 10.0):
        """Generate a list of dicts for dataset."""
        dataset = []
        for _ in range(num_trajectories):
            max_speed = self.rng.uniform(5.0, 30.0)
            traj = self.generate_straight_accel_decel(duration=length_sec, max_speed=max_speed)
            dataset.append(traj)
        return dataset
