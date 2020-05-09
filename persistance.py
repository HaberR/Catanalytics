import json
import datetime
from json import JSONEncoder


class StateEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


def save(state, file=None):
    if file is None:
        file = _get_new_save_location()
    with open(file, 'w+') as f:
        res = json.dumps(state, cls=StateEncoder)
        f.write(res)


def _get_new_save_location():
    instant = datetime.datetime.now()
    month, year, hour, minute = instant.month, instant.day, instant.hour, instant.minute
    return "Catan {0} {1} {2} {3}.json".format(month,year,hour,minute)
