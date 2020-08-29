from optimize import optimize_scenario
import pytest


def _create_inputs():
    return dict(marginal_ordinary_income_tax_rate=.0,
                current_state_ltcg_rate=.1,
                current_state_stcg_rate=.1,
                new_state_ltcg_rate=.1,
                new_state_stcg_rate=.1,
                federal_ltcg_rate=0,
                federal_stcg_rate=0,
                share_basis_price=10,
                pre_tax_num_shares=10,
                alternate_investment_rate_of_return=1.1,
                moving_costs=1)


def assert_results(results, stay_st=0.0, stay_lt=0.0, go_st=0.0, go_lt=0.0, name=None):
    assert results["current_state_stcg_num_shares"] == stay_st, name
    assert results["current_state_ltcg_num_shares"] == stay_lt, name
    assert results["new_state_stcg_num_shares"] == go_st, name
    assert results["new_state_ltcg_num_shares"] == go_lt, name


def assert_earnings(results, value, name=None):
    assert pytest.approx(results["objective"]) == value, name


def calculate_earnings(num_shares, basis, ror_6m, ror_12m, tax_6m, tax_12m):
    share_price_6m = basis * ror_6m
    share_price_12m = share_price_6m * ror_12m
    stcg_6m = share_price_6m - basis
    stcg_12m = share_price_12m - share_price_6m
    stcg_tax_6m = stcg_6m * tax_6m
    stcg_tax_12m = stcg_12m * tax_12m
    return num_shares * (basis + stcg_6m + stcg_12m - stcg_tax_6m - stcg_tax_12m)


def test_short_term_favored():
    inputs = _create_inputs()
    # higher long term tax rates cause short term to be favored
    inputs["current_state_ltcg_rate"] = .2
    inputs["new_state_ltcg_rate"] = .2

    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, stay_st=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.1, tax_12m=.1))

    # alternate rate used for second 6m
    inputs["alternate_investment_rate_of_return"] = 1.2
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.2, tax_6m=.1, tax_12m=.1))


def test_long_term_favored():
    inputs = _create_inputs()
    # higher short term tax rates cause long term to be favored
    inputs["current_state_stcg_rate"] = .2
    inputs["new_state_stcg_rate"] = .2

    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    # confirm it switches away from short term
    assert_results(results, stay_lt=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.1, tax_12m=.1))


def test_new_state_favored():
    inputs = _create_inputs()
    # higher current_state tax favors new_state
    inputs["current_state_stcg_rate"] = .8
    inputs["current_state_ltcg_rate"] = .9
    moving_cost = inputs["moving_costs"]

    # test new state stcg first
    inputs["new_state_ltcg_rate"] = .8
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, go_st=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.1, tax_12m=.1)
                    - moving_cost)
    assert results["is_moving"] == 1

    # test new state ltcg
    inputs["new_state_stcg_rate"] = .8
    inputs["new_state_ltcg_rate"] = .1
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, go_lt=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.1, tax_12m=.1)
                    - moving_cost)
    assert results["is_moving"] == 1

    # test moving costs switches it back
    inputs["moving_costs"] = 100000
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, stay_st=10.0)
    assert results["is_moving"] == 0
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.8, tax_12m=.8))


def test_federal_taxes_current_state():
    inputs = _create_inputs()

    # federal taxes applied to short term
    inputs["federal_stcg_rate"] = .1
    inputs["federal_ltcg_rate"] = .3
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, stay_st=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.2, tax_12m=.2))

    # federal taxes applied to long term
    inputs["federal_stcg_rate"] = .5
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, stay_lt=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.4, tax_12m=.4))


def test_federal_taxes_new_state():
    inputs = _create_inputs()

    # higher current_state tax favors new_state
    inputs["current_state_stcg_rate"] = .9
    inputs["current_state_ltcg_rate"] = .9
    moving_cost = inputs["moving_costs"]

    # federal taxes applied to short term
    inputs["federal_stcg_rate"] = .1
    inputs["federal_ltcg_rate"] = .3
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, go_st=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.2, tax_12m=.2)
                    - moving_cost)

    # federal taxes applied to long term
    inputs["federal_stcg_rate"] = .5
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1)
    assert_results(results, go_lt=10.0)
    assert_earnings(results,
                    calculate_earnings(num_shares=10, basis=10, ror_6m=1.1, ror_12m=1.1, tax_6m=.4, tax_12m=.4)
                    - moving_cost)


def test_tax_applied_to_shares():
    inputs = _create_inputs()

    inputs["marginal_ordinary_income_tax_rate"] = .5
    # break the tie between stcg and ltcg rates
    inputs["current_state_ltcg_rate"] = .2
    results = optimize_scenario(**inputs, rate_of_return_6m=1.1, rate_of_return_12m=1.1, debug=True)
    assert_results(results, stay_st=5.0)
