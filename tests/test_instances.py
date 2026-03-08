"""
Tests for the Multi-Period Blending Problem (MPBP) instances.

Run with:
    pytest tests/ -v
"""

import json
import os
import sys
import pytest
import pyomo.environ as pyo
from pyomo.opt import SolverStatus

# Make the project root importable when running pytest from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model import miqcp
from utilities import convert_json_to_data

INSTANCES_DIR = os.path.join(os.path.dirname(__file__), "..", "instances_json")
N_INSTANCES = 60

# Time limit (seconds) per solve for the smoke tests so the suite doesn't hang
SMOKE_TIME_LIMIT = 5


def load_instance(n: int) -> dict:
    path = os.path.join(INSTANCES_DIR, f"mpbp_{n}.json")
    with open(path, "r") as f:
        json_obj = json.load(f)
    return convert_json_to_data(json_obj)


def make_solver(time_limit: int | None = None):
    opt = pyo.SolverFactory("gurobi")
    if time_limit is not None:
        opt.options["TimeLimit"] = time_limit
    return opt


# ---------------------------------------------------------------------------
# Test 1: All instances build and are accepted by Gurobi (smoke test)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("instance_num", range(1, N_INSTANCES + 1))
def test_instance_runs(instance_num):
    """
    Every instance should load, build a valid Pyomo model, and be successfully
    submitted to Gurobi. We do not require a feasible or optimal solution —
    only that Gurobi accepts the model and returns a recognised status.
    """
    data = load_instance(instance_num)
    model = miqcp(data)

    opt = make_solver(time_limit=SMOKE_TIME_LIMIT)
    result = opt.solve(model, tee=False, load_solutions=False)

    # Gurobi must not report a hard solver error
    assert result.solver.status != SolverStatus.error, (
        f"Instance {instance_num}: Gurobi returned a solver error.\n"
        f"Solver status : {result.solver.status}\n"
        f"Termination  : {result.solver.termination_condition}"
    )


# ---------------------------------------------------------------------------
# Test 2: Instance 6 converges to the known optimal objective value
# ---------------------------------------------------------------------------

INSTANCE_6_OPTIMAL_OBJ = 337.15
OBJ_TOLERANCE = 1e-2  # absolute tolerance on the objective value


def test_instance_6_optimal():
    """
    Instance 6 must solve to optimality and achieve an objective value of
    337.15 (within an absolute tolerance of 1e-2).
    """
    data = load_instance(6)
    model = miqcp(data)

    opt = make_solver()
    result = opt.solve(model)

    # Require optimal termination
    pyo.assert_optimal_termination(result)

    obj_value = pyo.value(model.obj)
    assert abs(obj_value - INSTANCE_6_OPTIMAL_OBJ) <= OBJ_TOLERANCE, (
        f"Instance 6 objective mismatch: expected {INSTANCE_6_OPTIMAL_OBJ}, "
        f"got {obj_value:.6f} (tolerance {OBJ_TOLERANCE})"
    )
