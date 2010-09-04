import datetime
import pytz

utc_tz = pytz.timezone('UTC')

def utc_cast(dt):
    """
    @param dt:  A naive datetime
    @return:    The same datetime, considered UTC
    """
    return utc_tz.normalize(utc_tz.localize(dt))

def utcnow():
    return utc_cast(datetime.datetime.utcnow())
