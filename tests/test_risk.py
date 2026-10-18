import math
import numpy as np
import pytest
from app.risk import estimate, anytime_upper, drift


def test_zero_failures_do_not_mean_zero_risk():
    result=estimate([0]*10)
    assert result["expected_loss_usd"]>0
    assert result["frequency_ci95"][1]>0
    assert result["anytime_upper_usd"]>result["expected_loss_usd"]
    assert result["severity_counts"]==[0,0,0,0]


def test_prior_only_and_more_evidence():
    prior=estimate([])
    assert prior["status"]=="prior_only"
    assert prior["frequency_mean"]==0.5
    assert estimate([0]*100)["expected_loss_usd"]<estimate([0]*10)["expected_loss_usd"]<prior["expected_loss_usd"]


def test_frequency_and_severity_have_separate_effects():
    low=estimate([0]*9+[2500])
    high=estimate([0]*9+[100000])
    frequent=estimate([0]*5+[2500]*5)
    assert high["frequency_mean"]==low["frequency_mean"]
    assert high["expected_loss_usd"]>low["expected_loss_usd"]
    assert frequent["frequency_mean"]>low["frequency_mean"]


def test_beta_posterior_exact_mean_and_rounding():
    result=estimate([0,0,2501])
    assert result["frequency_mean"]==pytest.approx(1.5/4)
    assert result["severity_counts"]==[0,1,0,0]
    assert result["expected_loss_usd"]==pytest.approx(result["frequency_mean"]*result["severity_mean_usd"])
    assert estimate([0,0,2501])==result


@pytest.mark.parametrize("loss", [-1,100001,float("inf"),float("nan")])
def test_never_silently_clip_losses(loss):
    with pytest.raises(ValueError):estimate([loss])
    with pytest.raises(ValueError):anytime_upper([loss])


def test_sequential_bound_formula_and_alpha_budget():
    n=100
    radius=math.sqrt(math.log(math.pi**2*n*n/(0.05*6))/(2*n))
    assert anytime_upper([0]*n)==pytest.approx(100000*radius)
    assert sum(.05*6/(math.pi**2*t*t) for t in range(1,100001))<.05
    assert anytime_upper([])==100000


def test_anytime_coverage_monte_carlo_bounded_bernoulli():
    # 1500 full trajectories, not independent fixed-time spot checks.
    rng=np.random.default_rng(7)
    t=np.arange(1,401)
    for p in [.01,.1,.5]:
        values=rng.binomial(1,p,(1500,400))
        upper=np.minimum(1,values.cumsum(axis=1)/t+np.sqrt(np.log(math.pi**2*t*t/(.05*6))/(2*t)))
        ever_miss=np.any(upper<p,axis=1).mean()
        assert ever_miss<.05


def test_e_process_null_factor_and_latched_alert():
    assert .1*(1+3*(1-.1))+.9*(1+3*(0-.1))==pytest.approx(1)
    assert not drift([False]*20)["alert"]
    assert drift([True]*5+[False]*100)["alert"]
    assert drift([True]*5+[False]*100)["e_value"]<20
