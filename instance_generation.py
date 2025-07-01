import random
from utilities import data_preprocessing


class InstanceGenerator:
    def __init__(self) -> None:
        """
        Generates a multi-period blending problem instance based on network architecture and basic parameters.
        """
        self.d = {}
        self.has_sets = False
        self.has_parameters = False
        self.set_seed = True

    def seed(self, seed=None) -> None:
        """
        Sets seed

        Arguments
        ---------
        seed : int, optional
            Seed for reproducibility. Default is None.
        """
        random.seed(seed)

        if seed is not None:
            self.set_seed = True

    def build_sets(
        self,
        n_supply: int,
        blend_arch: list[int],
        n_demand: int,
        n_time: int,
        n_qual: int,
    ) -> dict:
        """
        Builds the sets for the instance

        Arguments
        ---------
        n_supply : int
            Number of supply tanks
        blend_arch: list[int]
            List of number of blending tanks per column
        n_demand: int
            Number of demand tanks
        n_time: int
            Number of time periods
        n_comp: int
            Number of qual

        Returns
        -------
        d : dict
            Dictionary containing the sets for the case study. Also stored as a class attribute.
        """

        assert not self.has_sets
        assert not self.has_parameters

        d = self.d

        d["_TF"] = n_time
        # -------------------------SETS-----------------------------
        d["S"] = [f"S{i}" for i in range(1, n_supply + 1)]  # supply nodes

        # set of blending tanks for each column
        for (k, num) in enumerate(blend_arch):
            d[f"_B_{k+1}"] = [f"B_{k+1}_{i}" for i in range(1, num + 1)]
            final_counter = k + 1

        # combined set of all blending tanks
        d["B"] = []
        for i in range(1, final_counter + 1):
            key = f"_B_{i}"
            d["B"].extend(d[key])

        d["D"] = [f"D{i}" for i in range(1, n_demand + 1)]  # demand nodes
        d["N"] = d["S"] + d["B"] + d["D"]  # all nodes

        d["Q"] = [f"Q{i}" for i in range(1, n_qual + 1)]  # qualities
        d["T"] = list(range(1, d["_TF"] + 1))  # Set of discrete time periods
        # Arcs
        d["A"] = []

        # supply to first column node arcs
        for s in d["S"]:
            for b in d["_B_1"]:
                d["A"].append((s, b))

        # Intermediate node connections
        for i in range(1, final_counter):
            for b_out in d[f"_B_{i}"]:
                for b_in in d[f"_B_{i+1}"]:
                    d["A"].append((b_out, b_in))

        # last column node to demand arcs
        for di in d["D"]:
            for b in d[f"_B_{final_counter}"]:
                d["A"].append((b, di))

        self.has_sets = True

        self.d = d

        return self.d

    def build_parameters(self, demand_TP: int, Fmax: int) -> dict:

        """
        Builds the parameters for the instance

        Arguments
        ---------
        demand_TP : int
            Time period at which demand is required
        Fmax : int
            Flow capacity of each arc in the network

        Returns
        -------
        d : dict
            Dictionary containing all the sets and parameters of the instance. Also stored as a class attribute.
        """
        assert (
            self.has_sets
        ), "Sets not defined. Please call .build_set() before this function"
        assert not self.has_parameters, "Parameters already defined."

        d = self.d

        # Choosing a disposal node
        disposal = random.choice(d["D"])  # Disposal node
        d["_disposal"] = disposal
        D_wo_disp = d["D"].copy()
        D_wo_disp.remove(disposal)  # Demand set without disposal node

        d = self.d

        d["Fmax"] = Fmax

        # Defining FIN and CIN parameters
        d["FIN"] = {
            (s, t): random.randint(0, int(0.8 * Fmax)) if t < demand_TP else 0
            for s in d["S"]
            for t in d["T"]
        }  # FIN is kept below 80% of FMAX
        d["CIN"] = {
            (q, s): round(random.uniform(0, 5), 2) for q in d["Q"] for s in d["S"]
        }  # CIN are random numbers chosen between 0 and 5

        d["F_bounds"] = {nn: (1, Fmax) for nn in d["A"]}
        d["C_bounds"] = {q: (0, max([d["CIN"][q, s] for s in d["S"]])) for q in d["Q"]}

        _max_flow = sum(d["FIN"].values())  # Maximum inlet flow into the system
        CMAX = max(list(d["CIN"].values()))  # Maximum concentration possible in system
        CMIN = min(list(d["CIN"].values()))  # Minimum concentration possible in system

        d["FD_bounds"] = {}
        # Setting FD_bounds for all demand nodes other than a disposal node
        for dem in D_wo_disp:
            for t in d["T"]:
                # No demand requirement before demand TP
                if t < demand_TP:
                    d["FD_bounds"][(dem, t)] = (0, Fmax)
                else:
                    # Demand lower bound is set as a number between 10% and 20% of the min flow in the system
                    _dem_flow_ub = min(
                        [Fmax, _max_flow]
                    )  # Demand flow requirements cannot be more than this number
                    dem_lb = random.randint(
                        round(0.1 * _dem_flow_ub, 0), round(0.3 * _dem_flow_ub, 0)
                    )
                    d["FD_bounds"][(dem, t)] = (dem_lb, Fmax)
        # Setting bounds for disposal nodes
        d["FD_bounds"].update({(disposal, t): (0, Fmax) for t in d["T"]})

        min_CD_bound = CMIN + (CMAX - CMIN) * 0.5

        d["CD_bounds"] = {
            (q, dem): (0, round(random.uniform(min_CD_bound, CMAX), 2))
            for q in d["Q"]
            for dem in D_wo_disp
        }  # Random concentration bounds for all demand sites except for the disposal node
        d["CD_bounds"].update(
            {(q, disposal): (0, CMAX) for q in d["Q"]}
        )  # bounds for disposal node

        # Inventory bounds
        d["I_bounds"] = {n: (0, 0) for n in d["N"]}
        for b in d["B"]:
            ub = random.randint(
                int(0.8 * Fmax), int(1.2 * Fmax)
            )  # the capacity of each inventory tank is a random number between 50% and 300% of Fmax
            d["I_bounds"][b] = (0, ub)  # updating inventory bounds for blending tanks

        # Initial Inventory
        d["I0"] = {n: 0 for n in d["N"]}
        d["C0"] = {(q, b): 0 for q in d["Q"] for b in d["B"]}

        # Costing parameters
        d["betaT_s"] = {s: random.randint(1, 10) for s in d["S"]}  # Supply cost
        d["betaT_d"] = {
            dem: random.randint(50, 70) for dem in D_wo_disp
        }  # Demand price
        d["betaT_d"][disposal] = random.randint(
            -10, -1
        )  # Negative cost for the disposal site
        max_cost = max(list(d["betaT_d"].values()))
        alpha_cost = round(random.uniform(0.3, 0.7), 2) * max_cost
        d["alphaN"] = {
            nn: alpha_cost for nn in d["A"]
        }  # fixed arc cost is a random number between 30 and 70% of the maximum betaT_d cost
        d["betaN"] = {
            nn: round(random.uniform(0.05, 0.8), 2) * alpha_cost for nn in d["A"]
        }  # variable arc cost is kept less than fixed cost

        self.d = d
        self.has_parameters = True

        d = self._check_and_adjust_FD_bounds(d)
        d = self._check_and_adjust_Inv_bounds(d)

        self.d = d

        return self.d

    def _check_and_adjust_FD_bounds(self, d):
        """
        Adjusts demand flow bounds when inlet flow is less than minimum demand requirements.

        Arguments
        ---------
        d : dict
            Dictionary containing the model data.
        """

        # Calculating inlet flow, minimum demand flow requirements and maximum demand flow requirements
        flow_in = sum(d["FIN"][s, t] for s in d["S"] for t in d["T"])
        min_flow_out = sum(d["FD_bounds"][dem, t][0] for dem in d["D"] for t in d["T"])
        max_flow_out = sum(d["FD_bounds"][dem, t][1] for dem in d["D"] for t in d["T"])

        assert (
            flow_in < max_flow_out
        ), "Inlet flow > Max demand requirement. Please inspect FIN."  # Based on definition this is not possible

        # Looping until inlet flow is sufficient to meet demand requirements
        while flow_in < min_flow_out:
            for dem in d["D"]:
                for t in d["T"]:
                    if d["FD_bounds"][dem, t][0] > 0:
                        lb = d["FD_bounds"][dem, t][0]
                        ub = d["FD_bounds"][dem, t][1]
                        new_lb = lb - 0.5 * lb  # Halving FD lower bound

                        d["FD_bounds"][dem, t] = (new_lb, ub)  # Setting new bounds
            # Recalculating minimum demand flow requirements
            min_flow_out = sum(
                d["FD_bounds"][dem, t][0] for dem in d["D"] for t in d["T"]
            )

        return d

    def _check_and_adjust_Inv_bounds(self, d):
        """
        Adjusts inventory capacities when current capacity is not sufficient to hold inlet flows.

        Arguments
        ---------
        d : dict
            Dictionary containing the model data.
        """
        # Calculating total inlet flow and current total inventory capacity
        flow_in = sum(d["FIN"][s, t] for s in d["S"] for t in d["T"])
        max_inv = sum(d["I_bounds"][b][1] for b in d["B"])

        # Looping until capacity is sufficient to meet inlet flows
        while flow_in > max_inv:
            # Increasing the capacity by 10%
            d["I_bounds"] = {
                key: (value[0], value[1] + 0.1 * value[1])
                for key, value in d["I_bounds"].items()
            }  # Adjusting bounds
            max_inv = sum(
                d["I_bounds"][b][1] for b in d["B"]
            )  # Recalculating maximum inventory

        return d


if __name__ == "__main__":
    inst_gen = InstanceGenerator()
    inst_gen.seed(42)
    inst_gen.build_sets(n_supply=3, blend_arch=[2, 4], n_demand=2, n_time=6, n_qual=1)
    d = inst_gen.build_parameters(demand_TP=4, Fmax=50)
    d = data_preprocessing(d)
