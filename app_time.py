"""Ephemeris time -> Python datetime (UTC), shared by the app and the pitch scripts."""
import datetime as dt

import numpy as np

import moon_sky as ms


def et_to_dt(ets):
    return [dt.datetime.fromisoformat(u) for u in ms.et_to_utc(np.atleast_1d(ets))]
