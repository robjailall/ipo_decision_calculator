from pulp import LpMaximize, LpProblem, LpStatus, LpVariable

# tax inputs
current_state_ltcg_rate = .13
current_state_stcg_rate = .13
new_state_ltcg_rate = 0
new_state_stcg_rate = 0
federal_ltcg_rate = .2
federal_stcg_rate = .33
moving_costs = 2000

# return inputs
share_basis_price = 120
short_term_price = 200
long_term_price = 150
num_shares = 5000
total_cost = num_shares * share_basis_price

# Create the model
model = LpProblem(name="optimize_returns", sense=LpMaximize)

# optimize variables
current_state_stcg_num_shares = LpVariable(name="current_state_stcg_num_shares", lowBound=0, upBound=num_shares)
current_state_ltcg_num_shares = LpVariable(name="current_state_ltcg_num_shares", lowBound=0, upBound=num_shares)
new_state_stcg_num_shares = LpVariable(name="new_state_stcg_num_shares", lowBound=0, upBound=num_shares)
new_state_ltcg_num_shares = LpVariable(name="new_state_ltcg_num_shares", lowBound=0, upBound=num_shares)
is_moving = LpVariable(name="is_moving", lowBound=0, upBound=1, cat="Integer")

# calculations
current_state_stcg = current_state_stcg_num_shares * (short_term_price - share_basis_price)
current_state_ltcg = current_state_ltcg_num_shares * (long_term_price - share_basis_price)
new_state_stcg = new_state_stcg_num_shares * (short_term_price - share_basis_price)
new_state_ltcg = new_state_ltcg_num_shares * (long_term_price - share_basis_price)
federal_stcg = current_state_stcg + new_state_stcg
federal_ltcg = current_state_ltcg + new_state_ltcg

# constraints
model += (num_shares == current_state_stcg_num_shares + current_state_ltcg_num_shares
          + new_state_stcg_num_shares + new_state_ltcg_num_shares,
          "total_shares_sum")

# make is_moving a flag dependent on whether we have new_state capital gains
model += (is_moving <= (new_state_stcg_num_shares + new_state_ltcg_num_shares),
          "new_state_shares_sold_dependency")
model += ((new_state_stcg_num_shares + new_state_ltcg_num_shares) <= is_moving * num_shares,
          "new_state_shares_sold_flag")

total_return = (current_state_stcg + new_state_stcg + current_state_ltcg + new_state_ltcg) \
               - current_state_stcg * (federal_stcg_rate + current_state_stcg_rate) \
               - current_state_ltcg * (federal_ltcg_rate + current_state_ltcg_rate) \
               - new_state_stcg * (federal_stcg_rate + new_state_stcg_rate) \
               - new_state_ltcg * (federal_ltcg_rate + new_state_ltcg_rate) \
               - moving_costs * is_moving

model += total_return
print(model)
status = model.solve()

print(f"status: {model.status}, {LpStatus[model.status]}")
print(f"objective: {model.objective.value()}")
for var in model.variables():
    print(f"{var.name}: {var.value()}")

for name, constraint in model.constraints.items():
    print(f"{name}: {constraint.value()}")
