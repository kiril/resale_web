# python
from datetime import datetime, date
import functools
import logging
import traceback

# libraries
from pymongo.objectid import ObjectId
import simplejson
import tornado.web

def datetime_iso_8601(dt):
    """
    @param dt:      A datetime
    @return:        The datetime as a string, according to the emerging consensus
                    about datetimes in JSON, something like:
                    1997-07-16T19:20:30.45+01:00
    """
    return dt.replace(microsecond=0).isoformat()

class DatetimeObjectIdEncoder(simplejson.JSONEncoder):
    """
    Convert datetimes to ISO-8601 strings while encoding a Python structure as JSON
    """
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return datetime_iso_8601(obj)
        if isinstance(obj, date):
            return datetime_iso_8601(datetime(obj.year, obj.month, obj.day))
        return simplejson.JSONEncoder.default( self, obj )

def jsonio(method):
    @functools.wraps(method)
    def g(self):
        self.set_header("Content-Type", "text/plain")            
        try:
            if self.request.method in ('POST', 'PUT'):
                json = simplejson.loads(self.get_argument('json'))
                logging.info('%s <= %s' % (
                    repr(self.request.path), repr(json)
                ))
            else:
                logging.info(repr(self.request.path))
                json = {}
            
            response = method(self, json)
            logging.info('%s => %s' % (
                repr(self.request.path), repr(response)
            ))
            self.write(simplejson.dumps(
                response,
                cls=DatetimeObjectIdEncoder
            ))
        except Exception, e:
            logging.error(traceback.format_exc())
            raise tornado.web.HTTPError(
                500,
                simplejson.dumps({
                    'result': 'failure',
                    'message':str(e)
                }),
            )
    return g


def chain(*decorators):
    def decorate(f):
        for d in reversed(decorators): f = d(f)
        return f
    return decorate
