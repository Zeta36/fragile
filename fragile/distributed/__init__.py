"""Module that includes scalable search algorithms."""
import sys

try:
    from fragile.distributed.distributed_export import DistributedExport
    from fragile.distributed.env import ParallelEnvironment, ParallelFunction, RayEnv
except (ImportError, ModuleNotFoundError) as e:
    if sys.version_info == (3, 7):
        raise e
