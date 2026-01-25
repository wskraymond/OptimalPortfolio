import random
import numpy as np
from collections import OrderedDict
from numba import int32, float32
from numba.experimental import jitclass

"""
For simplicity, I'm going to make the following assumptions:

the share price when the contract is signed =100 .
the strike price and the knock-out price are symmetric around $100.
the strike price = 100 - K
the knock-out price = 100 + k
the contract lasts for a year with 12 settlements and each month end.
the amount of shares to buy in each settlement:
A=1,000 if the share price at settlement is between the strike price and the knock-out price.
A=2,000 if the share prices settlement is below the strike price.
the monthly stock returns follow a normal distribution with mean zero and a standard deviation.
"""

"""
http://numba.pydata.org/

The simulation code I write below leverages Numba to speed up the calculation.

For 1 million simulations per pair of K,sigma(vol) , it takes about 2 seconds on my laptop with JIT and almost 1 minute without it.

"""

@jitclass(OrderedDict({
    'times': int32,
    'strike_price': float32,
    'knock_out_price': float32,
    'volatility': float32
}))
class FastSimulation:

    def __init__(self, times, strike_price, knock_out_price, volatility):
        self.times = times
        self.strike_price = strike_price
        self.knock_out_price = knock_out_price
        self.volatility = volatility

    def run(self):
        np.random.seed(1)
        buyer_payoffs = []
        for i in range(self.times):
            # generate 12 monthly returns from a normal distribution
            # written this way as size parameter is not supported by numba
            returns = [np.random.normal(
                loc=0, scale=self.volatility)/100 + 1 for _ in range(12)]
            # convert returns to a price array
            prices = np.asarray(returns).cumprod() * 100
            payoff = 0
            for price in prices:
                # the accumulator is terminated immediately
                if price > self.knock_out_price:
                    break
                payoff += self.buyer_payoff(price)
            buyer_payoffs.append(payoff)
        return buyer_payoffs

    def buyer_payoff(self, share_price):
        "Buyer payoff conditional on the accumulator not terminated"
        if share_price > self.knock_out_price:
            return 0
        payoff = 1000 * (share_price - self.strike_price)
        if self.strike_price <= share_price <= self.knock_out_price:
            return payoff
        else:
            return payoff * 2