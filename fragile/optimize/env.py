from typing import Callable

import numpy as np
import torch

from fragile.core.base_classes import BaseEnvironment, BaseStates
from fragile.core.states import States
from fragile.core.utils import device, to_tensor


class Function(BaseEnvironment):
    def __init__(self, function: Callable, shape, bounds=None, device=device, *args, **kwargs):
        super(Function, self).__init__(*args, **kwargs)
        self.function = function
        self.bounds = bounds
        self.shape = shape
        self.device = device
        self._last_states = None

    def __repr__(self):
        text = "{} with function {}, obs shape {}, and bounds: {}".format(
            self.__class__.__name__, self.function.__name__, self.shape, self.bounds
        )
        return text

    def get_params_dict(self) -> dict:
        """Return a dictionary containing the param_dict to build an instance
        of States that can handle all the data generated by the environment.
        """
        params = {
            "states": {"sizes": self.shape, "dtype": torch.int64, "device": self.device},
            "observs": {"sizes": self.shape, "dtype": torch.float, "device": self.device},
            "rewards": {"sizes": tuple([1]), "dtype": torch.float, "device": self.device},
            "ends": {"sizes": tuple([1]), "dtype": torch.uint8, "device": self.device},
        }
        return params

    def step(
        self,
        actions: [torch.Tensor, np.ndarray],
        env_states: BaseStates,
        n_repeat_action: [int, np.ndarray] = 1,
        *args,
        **kwargs
    ) -> BaseStates:
        """
        Sets the environment to the target states by applying the specified actions an arbitrary
        number of time steps.

        Args:
            actions: Vector containing the actions that will be applied to the target states.
            env_states: BaseStates class containing the state data to be set on the Environment.
            n_repeat_action: Number of times that an action will be applied. If it is an array
                it corresponds to the different dts of each walker.
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            States containing the information that describes the new state of the Environment.
        """
        states = to_tensor(env_states.states, device=self.device)
        actions = to_tensor(actions, device=self.device)
        n_repeat_action = to_tensor(n_repeat_action, device=self.device)
        new_points = actions.float() * n_repeat_action.float() + states.float()
        # new_points[-1] = states[-1].detach().clone()

        rewards = self.function(new_points)
        # rewards[-1] = env_states.rewards[-1]
        ends = self.boundary_condition(new_points, rewards)

        # ends[-1] = 0
        self._last_states = self._get_new_states(new_points, rewards, ends, len(actions))
        return self._last_states

    def boundary_condition(self, points, rewards):
        ends = torch.ones(rewards.shape, dtype=torch.uint8, device=self.device)
        ends[self.are_in_bounds(points)] = 0
        return ends

    def _sample_init_points(self, batch_size: int):
        new_points = torch.zeros(
            tuple([batch_size]) + self.shape, dtype=torch.float32, device=self.device
        )
        for i in range(batch_size):
            new_points[i, :] = to_tensor(
                [np.random.uniform(l, h) for l, h in self.bounds],
                dtype=torch.float32,
                device=self.device,
            )
        return new_points

    def reset(self, batch_size: int = 1, states=None) -> BaseStates:
        """
        Resets the environment to the start of a new episode and returns an
        States instance describing the state of the Environment.
        Args:
            batch_size: Number of walkers that the returned state will have.
            states: Ignored.

        Returns:
            States instance describing the state of the Environment. The first
            dimension of the data tensors (number of walkers) will be equal to
            batch_size.
        """
        # rewards = torch.ones(batch_size, dtype=torch.float32, device=self.device) * -1e20
        ends = torch.zeros(batch_size, dtype=torch.uint8, device=self.device)
        new_points = self._sample_init_points(batch_size=batch_size)
        rewards = self.function(new_points)
        new_states = self._get_new_states(new_points, rewards, ends, batch_size=batch_size)
        return new_states

    def are_in_bounds(self, states):
        in_bounds = torch.ones(len(states), dtype=torch.uint8, device=self.device)
        if self.bounds is None:
            return in_bounds
        for i, (min_val, max_val) in enumerate(self.bounds):
            valid_min = states[:, i] > min_val
            # print("valid_min", valid_min, min_val, states)
            valid_max = states[:, i] < max_val
            # print("valid_max", valid_max, max_val, states)
            valid_vector = valid_max & valid_min
            in_bounds = valid_vector & in_bounds
        return in_bounds

    def _get_new_states(self, states, rewards, ends, batch_size) -> BaseStates:
        state = States(state_dict=self.get_params_dict(), n_walkers=batch_size)
        state.update(
            states=states, observs=states, rewards=rewards.reshape(-1, 1), ends=ends.reshape(-1, 1)
        )
        return state
