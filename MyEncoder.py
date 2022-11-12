"""
An encoder to help solving self-designed class and np-array's dump problem
Designed class Option for parameter store
"""
import datetime
import json
import numpy as np


class Option(object):
    def __init__(self, node_address, s, tm, c_s, sigma, x, y):
        """
        Construct Option class
        :param node_address: Address of node
        :param s: Mutation Strength
        :param tm: Transform Matrix
        :param c_s: Learning Rate of Evolution Path
        :param sigma: Step Size
        :param x: Solution
        :param y: Value of Solution
        """
        self.node_address = node_address
        self.s = s
        self.tm = tm
        self.c_s = c_s
        self.sigma = sigma
        self.x = x
        self.y = y


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Option):
            return obj.__dict__
        else:
            return super(MyEncoder, self).default(obj)
