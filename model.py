import pyomo.environ as pyo
import json
from utilities import convert_json_to_data, data_preprocessing
from instance_generation import InstanceGenerator


def miqcp(data):
    # PYOMO MODEL
    m = pyo.ConcreteModel()

    # SETS
    m.S = pyo.Set(initialize=data["S"])  # Set of supply tanks
    m.B = pyo.Set(initialize=data["B"])  # Set of blending tanks
    m.D = pyo.Set(initialize=data["D"])  # Set of demand tanks
    m.N = pyo.Set(initialize=data["N"])  # Set of tanks
    m.Q = pyo.Set(initialize=data["Q"])  # Set of substances
    m.T = pyo.Set(initialize=data["T"])  # Set of discrete time periods
    m.A = pyo.Set(initialize=data["A"])  # Set of existing arcs

    # PARAMETERS
    # Arc dependencies
    m.Nin = pyo.Param(m.N, initialize=data["Nin"], within=pyo.Any)
    m.Nout = pyo.Param(m.N, initialize=data["Nout"], within=pyo.Any)

    # Initial inventories
    m.I0 = pyo.Param(m.N, initialize=data["I0"], within=pyo.NonNegativeReals)

    # Initial composition
    m.C0 = pyo.Param(m.Q, m.B, initialize=data["C0"], within=pyo.NonNegativeReals)

    # Inventory bounds
    m.I_bounds = pyo.Param(m.N, initialize=data["I_bounds"], within=pyo.Any)

    # Flow bounds
    m.F_bounds = pyo.Param(m.A, initialize=data["F_bounds"], within=pyo.Any)
    m.Fmax = pyo.Param(initialize=data["Fmax"], within=pyo.NonNegativeReals)

    # Demanded flow bounds
    m.FD_bounds = pyo.Param(m.D, m.T, initialize=data["FD_bounds"], within=pyo.Any)

    # Demanded composition bounds
    m.CD_bounds = pyo.Param(m.Q, m.D, initialize=data["CD_bounds"], within=pyo.Any)

    # Composition bounds
    m.C_bounds = pyo.Param(m.Q, initialize=data["C_bounds"], within=pyo.Any)

    # Supply conditions
    m.CIN = pyo.Param(m.Q, m.S, initialize=data["CIN"], within=pyo.NonNegativeReals)
    m.FIN = pyo.Param(m.S, m.T, initialize=data["FIN"], within=pyo.NonNegativeReals)

    # Economic parameters
    m.betaT_s = pyo.Param(m.S, initialize=data["betaT_s"], within=pyo.Reals)
    m.betaT_d = pyo.Param(m.D, initialize=data["betaT_d"], within=pyo.Reals)
    m.alphaN = pyo.Param(m.A, initialize=data["alphaN"], within=pyo.Reals)
    m.betaN = pyo.Param(m.A, initialize=data["betaN"], within=pyo.Reals)

    # CONTINUOUS VARIABLES
    m.F = pyo.Var(m.A, m.T, within=pyo.NonNegativeReals, bounds=(0, m.Fmax))
    m.FD = pyo.Var(
        m.D, m.T, within=pyo.NonNegativeReals, bounds=lambda _, d, t: m.FD_bounds[d, t]
    )
    m.I = pyo.Var(
        m.N, m.T, within=pyo.NonNegativeReals, bounds=lambda _, n, t: m.I_bounds[n]
    )
    m.C = pyo.Var(
        m.Q,
        m.B,
        m.T,
        within=pyo.NonNegativeReals,
        bounds=lambda _, q, b, t: m.C_bounds[q],
    )

    # BINARY VARIABLES
    m.X = pyo.Var(m.A, m.T, within=pyo.Binary)

    # CONSTRAINTS

    # Flow activation
    @m.Constraint(m.A, m.T)
    def flow_activation_L(m, nin, nout, t):
        return m.F_bounds[nin, nout][0] * m.X[nin, nout, t] <= m.F[nin, nout, t]

    @m.Constraint(m.A, m.T)
    def flow_activation_U(m, nin, nout, t):
        return m.F[nin, nout, t] <= m.F_bounds[nin, nout][1] * m.X[nin, nout, t]

    # Satisfy Blending specifications
    @m.Constraint(m.Q, m.A, m.T)
    def blend_specs_L(m, q, b, d, t):
        if b in m.B and d in m.D and t > 1:
            return (
                m.CD_bounds[q, d][0] - m.C_bounds[q][1] * (1 - m.X[b, d, t])
                <= m.C[q, b, t - 1]
            )  # changed to upper bound M
        else:
            return pyo.Constraint.Skip

    @m.Constraint(m.Q, m.A, m.T)
    def blend_specs_U(m, q, b, d, t):
        if b in m.B and d in m.D and t > 1:
            return m.C[q, b, t - 1] <= m.CD_bounds[q, d][1] + m.C_bounds[q][1] * (
                1 - m.X[b, d, t]
            )
        else:
            return pyo.Constraint.Skip

    # Satisfy SD specifications
    @m.Constraint(m.Q, m.A, m.T)
    def sd_specs_L(m, q, s, d, t):
        if s in m.S and d in m.D:
            return (
                m.CD_bounds[q, d][0] - m.C_bounds[q][1] * (1 - m.X[s, d, t])
                <= m.CIN[q, s]
            )  # changed to upper bound M
        else:
            return pyo.Constraint.Skip

    @m.Constraint(m.Q, m.A, m.T)
    def sd_specs_U(m, q, s, d, t):
        if s in m.S and d in m.D:
            return m.CIN[q, s] <= m.CD_bounds[q, d][1] + m.C_bounds[q][1] * (
                1 - m.X[s, d, t]
            )
        else:
            return pyo.Constraint.Skip

    # Supply inventory balance
    @m.Constraint(m.S, m.T)
    def supply_bal(m, s, t):
        if t == 1:
            return m.I[s, t] == m.I0[s] + m.FIN[s, t] - sum(
                m.F[s, n, t] for n in m.Nout[s]
            )
        else:
            return m.I[s, t] == m.I[s, t - 1] + m.FIN[s, t] - sum(
                m.F[s, n, t] for n in m.Nout[s]
            )

    # Blending inventory balances
    @m.Constraint(m.B, m.T)
    def blend_bal(m, b, t):
        if t == 1:
            return m.I[b, t] == m.I0[b] + sum(m.F[n, b, t] for n in m.Nin[b]) - sum(
                m.F[b, n, t] for n in m.Nout[b]
            )
        else:
            return m.I[b, t] == m.I[b, t - 1] + sum(
                m.F[n, b, t] for n in m.Nin[b]
            ) - sum(m.F[b, n, t] for n in m.Nout[b])

    # Demand inventory balance
    @m.Constraint(m.D, m.T)
    def demand_bal(m, d, t):
        if t == 1:
            return (
                m.I[d, t] == m.I0[d] + sum(m.F[n, d, t] for n in m.Nin[d]) - m.FD[d, t]
            )
        else:
            return (
                m.I[d, t]
                == m.I[d, t - 1] + sum(m.F[n, d, t] for n in m.Nin[d]) - m.FD[d, t]
            )

    # Bilinear balance
    @m.Constraint(m.Q, m.B, m.T)
    def bilinear_bal(m, q, b, t):
        if t == 1:
            return m.I[b, t] * m.C[q, b, t] == m.I0[b] * m.C0[q, b] + sum(
                m.F[s, b, t] * m.CIN[q, s] for s in m.S if (s, b) in m.A
            ) + sum(m.F[bb, b, t] * m.C0[q, bb] for bb in m.B if (bb, b) in m.A) - sum(
                m.F[b, n, t] * m.C0[q, b] for n in m.Nout[b]
            )
        else:
            return m.I[b, t] * m.C[q, b, t] == m.I[b, t - 1] * m.C[q, b, t - 1] + sum(
                m.F[s, b, t] * m.CIN[q, s] for s in m.S if (s, b) in m.A
            ) + sum(
                m.F[bb, b, t] * m.C[q, bb, t - 1] for bb in m.B if (bb, b) in m.A
            ) - sum(
                m.F[b, n, t] * m.C[q, b, t - 1] for n in m.Nout[b]
            )

    # Variable implication
    @m.Constraint(m.A, m.A, m.T)
    def implication(m, nin1, nout1, nin2, nout2, t):
        if nout1 in m.B and nout1 == nin2:
            return m.X[nin1, nout1, t] + m.X[nin2, nout2, t] <= 1
        else:
            return pyo.Constraint.Skip

    # OBJECTIVE
    @m.Objective(sense=pyo.maximize)
    def obj(m):
        return sum(
            sum(m.betaT_d[d] * m.F[n, d, t] for d in m.D for n in m.Nin[d])
            - sum(m.betaT_s[s] * m.F[s, n, t] for s in m.S for n in m.Nout[s])
            - sum(
                m.alphaN[nin, nout] * m.X[nin, nout, t]
                + m.betaN[nin, nout] * m.F[nin, nout, t]
                for (nin, nout) in m.A
            )
            for t in m.T
        )

    m.is_master = False

    return m


if __name__ == "__main__":
    # Opening instance
    with open('instances_json/instance_7.json', 'r') as f:
        json_obj = json.load(f)
    d = convert_json_to_data(json_obj)

    m = miqcp(d)    # building model
    
    # Solving with gurobi. If gurobi unavailable - can use any MIQCP/MINLP solver of choice
    opt = pyo.SolverFactory('gurobi')
    status = opt.solve(m, tee=True)

    # Ensure optimal termination
    pyo.assert_optimal_termination(status)

