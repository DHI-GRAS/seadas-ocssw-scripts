"""
Module to hold time utility classes and functions.
"""

import datetime

def convert_month_day_to_doy(mon, dom, yr):
    """
    Returns a day of year computed from the provided month (mon parameter),
    day of month(dom parameter), and year (yr parameter).
    """
    date_obj = datetime.datetime(int(yr), int(mon), int(dom))
    doy = date_obj.timetuple().tm_yday
    return doy

