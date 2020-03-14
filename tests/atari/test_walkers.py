import pytest

from hypothesis import given
from hypothesis.extra.numpy import arrays
import numpy

from fragile.atari.walkers import AtariWalkers
from tests.core.test_walkers import TestWalkers

N_WALKERS = 21


def get_atari_walkers_discrete_gym():
    env_params = {
        "states": {"size": (128,), "dtype": numpy.int64},
        "observs": {"size": (160, 210, 3), "dtype": numpy.float32},
        "rewards": {"dtype": numpy.float32},
        "ends": {"dtype": numpy.bool_},
        "game_ends": {"dtype": numpy.bool_},
    }
    model_params = {
        "actions": {"size": (10,), "dtype": numpy.int64},
        "dt": {"size": None, "dtype": numpy.float32},
        "critic": {"size": None, "dtype": numpy.float32},
    }
    return AtariWalkers(
        n_walkers=N_WALKERS, env_state_params=env_params, model_state_params=model_params
    )


walkers_config = {"discrete-atari-gym": get_atari_walkers_discrete_gym}
walkers_fixture_params = ["discrete-atari-gym"]


class TestAtariWalkers(TestWalkers):
    @pytest.fixture(params=walkers_fixture_params)
    def walkers(self, request):
        return walkers_config.get(request.param)()

    def test_calculate_end_condition(self, walkers):
        walkers.reset()
        walkers.states.update(ends=numpy.ones(walkers.n))
        walkers.env_states.update(game_ends=numpy.ones(walkers.n))
        assert walkers.calculate_end_condition()

    @given(observs=arrays(numpy.float32, shape=(N_WALKERS, 160, 210, 3)))
    def test_distances_not_crashes(self, walkers, observs):
        walkers.env_states.update(observs=observs)
        walkers.calculate_distances()
        assert isinstance(walkers.states.distances[0], numpy.float32)
        assert len(walkers.states.distances.shape) == 1
        assert walkers.states.distances.shape[0] == walkers.n