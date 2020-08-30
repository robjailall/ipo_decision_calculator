import csv
import math
import typing
from argparse import ArgumentParser
from csv import DictWriter
from sys import stdout

from pulp import LpMaximize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD


def ca_to_nv_tax_inputs() -> dict:
    return dict(rsu_witholding_rate=.22,
                current_state_ltcg_tax_rate=.13,
                current_state_stcg_tax_rate=.13,
                new_state_ltcg_tax_rate=0,
                new_state_stcg_tax_rate=0,
                federal_ltcg_tax_rate=.2,
                federal_stcg_tax_rate=.33)


def optimize_scenario(rate_of_return_6m: float,
                      rate_of_return_12m: float,
                      rsu_witholding_rate: float,
                      current_state_ltcg_tax_rate: float,
                      current_state_stcg_tax_rate: float,
                      new_state_ltcg_tax_rate: float,
                      new_state_stcg_tax_rate: float,
                      federal_ltcg_tax_rate: float,
                      federal_stcg_tax_rate: float,
                      share_basis_price: float,
                      pre_tax_num_shares: float,
                      alternate_investment_rate_of_return: float,
                      moving_costs: float,
                      debug: bool = False) -> dict:
    """
    This is the meat of the script that calculates the optimal number of shares to sell for short and long term tax
    rates and in your current or new state. It models this as a linear programming problem, which finds the variable
    values that maximize the objective function given constraints.
    """

    # Derived inputs
    post_tax_num_shares = pre_tax_num_shares * (1 - rsu_witholding_rate)

    # Create the linear programming model
    model = LpProblem(name="optimize_returns", sense=LpMaximize)

    # Variables that will be optimized in the model
    current_state_stcg_num_shares = LpVariable(name="current_state_stcg_num_shares", lowBound=0,
                                               upBound=post_tax_num_shares)
    current_state_ltcg_num_shares = LpVariable(name="current_state_ltcg_num_shares", lowBound=0,
                                               upBound=post_tax_num_shares)
    new_state_stcg_num_shares = LpVariable(name="new_state_stcg_num_shares", lowBound=0, upBound=post_tax_num_shares)
    new_state_ltcg_num_shares = LpVariable(name="new_state_ltcg_num_shares", lowBound=0, upBound=post_tax_num_shares)
    is_moving = LpVariable(name="is_moving", lowBound=0, upBound=1, cat="Integer")

    # Calculations used in the constraints and objective functions below
    short_term_price = share_basis_price * rate_of_return_6m
    long_term_price = short_term_price * rate_of_return_12m
    current_state_stcg = current_state_stcg_num_shares * (short_term_price - share_basis_price)
    current_state_ltcg = current_state_ltcg_num_shares * (long_term_price - share_basis_price)
    new_state_stcg = new_state_stcg_num_shares * (short_term_price - share_basis_price)
    new_state_ltcg = new_state_ltcg_num_shares * (long_term_price - share_basis_price)
    current_state_short_term_proceeds = current_state_stcg_num_shares * short_term_price
    current_state_alternate_investment_gain = (current_state_short_term_proceeds * alternate_investment_rate_of_return) \
                                              - current_state_short_term_proceeds
    new_state_short_term_proceeds = new_state_stcg_num_shares * short_term_price
    new_state_alternate_investment_gain = (new_state_short_term_proceeds * alternate_investment_rate_of_return) \
                                          - new_state_short_term_proceeds
    total_capital_gains = current_state_stcg + new_state_stcg + current_state_ltcg + new_state_ltcg \
                          + current_state_alternate_investment_gain + new_state_alternate_investment_gain
    post_tax_capital = post_tax_num_shares * share_basis_price

    # Constraints of the model
    model += (post_tax_num_shares == current_state_stcg_num_shares + current_state_ltcg_num_shares
              + new_state_stcg_num_shares + new_state_ltcg_num_shares,
              "total_shares_sum")

    # Makes is_moving a flag dependent on whether we have new_state capital gains
    model += (is_moving <= (new_state_stcg_num_shares + new_state_ltcg_num_shares),
              "new_state_shares_sold_dependency")
    model += ((new_state_stcg_num_shares + new_state_ltcg_num_shares) <= is_moving * post_tax_num_shares,
              "new_state_shares_sold_flag")

    # Objective function we are optimizing
    total_earnings = (post_tax_capital + total_capital_gains) \
                     - current_state_stcg * (federal_stcg_tax_rate + current_state_stcg_tax_rate) \
                     - current_state_ltcg * (federal_ltcg_tax_rate + current_state_ltcg_tax_rate) \
                     - new_state_stcg * (federal_stcg_tax_rate + new_state_stcg_tax_rate) \
                     - new_state_ltcg * (federal_ltcg_tax_rate + new_state_ltcg_tax_rate) \
                     - current_state_alternate_investment_gain * (federal_stcg_tax_rate + current_state_stcg_tax_rate) \
                     - new_state_alternate_investment_gain * (federal_stcg_tax_rate + new_state_stcg_tax_rate) \
                     - moving_costs * is_moving
    model += total_earnings

    msg = False
    if debug:
        msg = True
    status = model.solve(PULP_CBC_CMD(msg=msg))
    if status != 1:
        print(f"status: {model.status}, {LpStatus[model.status]}")
        raise Exception("No solution for scenario")

    if debug:
        print(model)
        for name, constraint in model.constraints.items():
            print(f"{name}: {constraint.value()}")

        for var in model.variables():
            print(f"{var.name}: {var.value()}")

    results = {
        "short_term_price": short_term_price,
        "long_term_price": long_term_price,
        "rate_of_return_6m": rate_of_return_6m,
        "rate_of_return_12m": rate_of_return_12m,
        "objective": model.objective.value(),
    }
    for var in model.variables():
        results[var.name] = var.value()

    return results


def print_results_tsv(rowdicts: typing.List[dict], f: typing.IO = stdout):
    writer = DictWriter(f=f,
                        extrasaction="ignore",
                        delimiter="\t",
                        fieldnames=["rate_of_return_6m",
                                    "rate_of_return_12m",
                                    "short_term_price",
                                    "long_term_price",
                                    "current_state_stcg_num_shares",
                                    "current_state_ltcg_num_shares",
                                    "new_state_stcg_num_shares",
                                    "new_state_ltcg_num_shares",
                                    "is_moving",
                                    "objective"])
    writer.writeheader()
    writer.writerows(rowdicts)


def _format_heatmap_cell(row: dict) -> str:
    """
    Formats the output of each cell in the heatmap
    """
    key_map = {"current_state_stcg_num_shares": "stay st",
               "current_state_ltcg_num_shares": "stay lt",
               "new_state_stcg_num_shares": "go st",
               "new_state_ltcg_num_shares": "go lt"}
    for key in key_map.keys():
        if row[key] > 0:
            return "{}   - {}".format(math.floor(row["objective"] / 1000.0), key_map[key])


def print_heat_map(rowdicts: typing.List[dict], short_term_rates_of_return: typing.List[float],
                   long_term_rates_of_return: typing.List[float], f: typing.IO = stdout):
    results_by_prices = {}
    for row in rowdicts:
        results_by_prices[(row["rate_of_return_6m"], row["rate_of_return_12m"])] = _format_heatmap_cell(row)

    header = ["First 6m Rate of Return"] + list(map(str, long_term_rates_of_return))
    data = []
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(header)

    for short_term_rate in short_term_rates_of_return:
        row = [short_term_rate]
        for long_term_rate in long_term_rates_of_return:
            row.append(results_by_prices[(short_term_rate, long_term_rate)])
        data.append(row)

    writer.writerows(data)


def main(share_basis_price: float,
         pre_tax_num_shares: float,
         alternate_investment_rate_of_return: float,
         moving_costs: float,
         debug: bool = False,
         output_dir: str = None):
    """
    Produces all of the data for the heatmap and outputs it
    """
    rates_of_return = [percent / 100.0 for percent in range(80, 105, 5)] \
                      + [percent / 100.0 for percent in range(100, 111, 1)] \
                      + [percent / 100.0 for percent in range(115, 205, 5)]

    rows = []
    for rate_of_return_6m in rates_of_return:
        for rate_of_return_12m in rates_of_return:
            rows.append(optimize_scenario(rate_of_return_6m=rate_of_return_6m,
                                          rate_of_return_12m=rate_of_return_12m,
                                          share_basis_price=share_basis_price,
                                          pre_tax_num_shares=pre_tax_num_shares,
                                          alternate_investment_rate_of_return=alternate_investment_rate_of_return,
                                          moving_costs=moving_costs,
                                          **ca_to_nv_tax_inputs(),
                                          debug=debug))
            if debug:
                break
        if debug:
            break

    with open(file="{}/ipo_data.tsv".format(output_dir) if output_dir else "/dev/stdout", mode="w") as f:
        print_results_tsv(rowdicts=rows, f=f)

    with open(file="{}/heatmap.tsv".format(output_dir) if output_dir else "/dev/stdout", mode="w") as f:
        print_heat_map(rowdicts=rows,
                       short_term_rates_of_return=rates_of_return,
                       long_term_rates_of_return=rates_of_return,
                       f=f)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--output-dir", type=str, default=None, help="Script will save tab-separated files here")
    parser.add_argument("--num-shares", type=float, default=5000.0, help="Pre-tax number of shares vested")
    parser.add_argument("--moving-costs", type=float, default=30000.0,
                        help="The amount of money it would take in expenses and tax savings to get you to move")
    parser.add_argument("--ipo-price", type=float, default=120.0,
                        help="This is the bases from which the script will calculate capital gains")
    parser.add_argument("--interest-rate", type=float, default=1.07,
                        help="This is the rate of return that you expect from "
                             "selling your shares and investing elsewhere")

    args = parser.parse_args()
    main(debug=args.debug,
         output_dir=args.output_dir,
         pre_tax_num_shares=args.num_shares,
         share_basis_price=args.ipo_price,
         moving_costs=args.moving_costs,
         alternate_investment_rate_of_return=args.interest_rate)
