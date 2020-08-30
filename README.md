# IPO Decision Calculator

Use this script to decide when (short term or long term capital gains) and in what state (different tax rates) you should sell your initial public offering (IPO) shares.

The decision depends on tax rates, return rates on your IPO shares and other investments, and the costs to move to the new state. The script outputs the optimal financial decision giving the combination of all these factors.

I've included the current (2020) tax rates for California (high tax) and Nevada (low tax) and current federal short and long term capital gains tax rates and marginal income tax rate.

## Notes

- The script assumes you are picking between selling your shares 6 months after IPO (likely after of a lockup period) or after 12 months (to get long term capital gains rates). If it recommends selling at 6 months, it assumes you use those proceeds to invest in something else that gets a return over the remaining 6 months. It then assumes you sell this investment at the end of the remaining 6 months at short term capital gains rates.
- `Moving Cost` is a key parameter -- the higher this cost, the more likely you should stay put. It doesn't have to only represent moving expenses. You can also think of it as the minimum amount of money or taxes saved it would take to get you to move.
- There's a known bug in calculating the taxes when there market has negative returns. It affects the return number the script spits out, but it doesn't affect the decision.

## Setup

```
git clone git@github.com:robjailall/ipo_decision_calculator.git
cd ipo_decision_calculator
pip install -r requirements.txt
pytest -v
python optimize.py --output-dir=/tmp
```

## Usage

```
usage: optimize.py [-h] [--debug] [--output-dir OUTPUT_DIR]
                   [--num-shares NUM_SHARES] [--moving-costs MOVING_COSTS]
                   [--ipo-price IPO_PRICE] [--interest-rate INTEREST_RATE]

optional arguments:
  -h, --help            show this help message and exit
  --debug
  --output-dir OUTPUT_DIR
                        Script will save tab-separated files here
  --num-shares NUM_SHARES
                        Pre-tax number of shares vested
  --moving-costs MOVING_COSTS
                        The amount of money it would take in expenses and tax
                        savings to get you to move
  --ipo-price IPO_PRICE
                        This is the bases from which the script will calculate
                        capital gains
  --interest-rate INTEREST_RATE
                        This is the rate of return that you expect from
                        selling your shares and investing elsewhere
                        
````

## Customization

The command line arguments cover the inputs that are likely specific to each individual. If you want to change the tax rates, look at the function `ca_to_nv_tax_inputs` in **optimize.py** as an example.
