"""Machine learning models for motion intelligence."""

from core.models.dataset_generator import SyntheticTrajectoryGenerator
from core.models.velocity_estimator import VelocityEstimatorAPI

try:
    from core.models.velocity_estimator import Velocity1DCNN
    __all__ = ['SyntheticTrajectoryGenerator', 'VelocityEstimatorAPI', 'Velocity1DCNN']
except ImportError:
    # PyTorch not available
    __all__ = ['SyntheticTrajectoryGenerator', 'VelocityEstimatorAPI']
