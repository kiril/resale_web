from pymongo.son_manipulator import SONManipulator
from pymongo.connection import Connection
import pymongo

class Datefix(SONManipulator):
    def transform_outgoing(self, obj, collection):
        if isinstance(obj, dict):
            from dateutil.parser import parse
            for k,v in obj.items():
                if isinstance(v, basestring) and ('date' in k or 'time' in k) and 'zone' not in k:
                    obj[k] = parse(v)
        elif isinstance(obj, list):
            for x in obj:
                self.transform_outgoing(x, collection)
        return obj

    def transform_incoming(self, obj, collection):
        if isinstance(obj, dict):
            from dateutil.parser import parse
            for k,v in obj.items():
                if isinstance(v, basestring) and ('date' in k or 'time' in k or k == 'first_save') and 'zone' not in k:
                    obj[k] = parse(v)
                elif isinstance(v, dict):
                    obj[k] = self.transform_incoming(v, collection)
        elif isinstance(obj, list):
            for x in obj:
                self.transform_incoming(x, collection)
        return obj

mongo = Connection('localhost')
resale_db = mongo['resale']
resale_db.add_son_manipulator(Datefix())
