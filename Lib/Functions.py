from munch import Munch

def munchify(**kwargs):
    return Munch.fromDict(kwargs)