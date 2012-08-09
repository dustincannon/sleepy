"""
Sleepy Decorators

Decorators that implement "guards" or functions that wrap around API methods to
handle preconditions before functions are called. For example "in order to call
this method the user should be authenticated", "in order to call this method
you must pass this parameter" etc.

:author: Adam Haney
:organization: Retickr
:contact: adam.haney@retickr.com
:license: Copyright (c) 2011 retickr, LLC
"""

__author__ = "Adam Haney <adam.haney@retickr.com>"
__license__ = "Copyright (c) 2011 retickr, LLC"

import json

# Thirdparty imports
from django.conf import settings

# Retickr imports
import sleepy.helpers

def create_mysql_connection():
    import MySQLdb
    return MySQLdb.connect(
        host=settings.MYSQL["HOST"],
        user=settings.MYSQL["USER"],
        passwd=settings.MYSQL["PASSWORD"],
        db=settings.MYSQL["NAME"])

def RequiresMySQLConnection(fn):
    """
    This decorator opens a mysql connection, does exception handling and on
    success passes the mysql connection to the wrapped function in
    self.mysql_conn
    """
    def _connect(*args, **kwargs):
        self.mysql_conn = create_mysql_connection()
        return fn(*args, **kwargs)
    return _connect


def create_cassandra_connection():
    import pycassa
    return pycassa.connect(
        settings.CASSANDRA["keyspace"],
        settings.CASSANDRA["hosts"],
        settings.CASSANDRA["credentials"])

def RequiresCassandraConnection(fn):
    """
    This decorator opens a pycassa connection to Cassandra.
    """
    def _wrap(fn):
        def _connect(*args, **kwargs):

            if not hasattr(self, "cassandra_connection"):
                self.cassandra_connection = create_cassandra_connection()
            return fn(*args, **kwargs)
        return _connect
    return _wrap

def RequiresParameters(params):
    """
    This is decorator that makes sure the function it wraps has received a
    given parameter in the request.REQUEST object. If the wrapped function
    did not receive this parameter it throws a django response containing
    an error and bails out
    """
    def _wrap(fn):
        def _check(*args, **kwargs):
            if set(params) < set(request.REQUEST):
                kwargs.update(request.REQUEST)
                return fn(*args, **kwargs)
            else:
                return self.json_err(
                    "{0} reqs to {1} should contain the {2} parameter".format(
                        fn.__name__,
                        self.__class__.__name__,
                        param
                        )
                    )
        return _check
    return _wrap


def RequiresUrlAttribute(param):
    """
    This is a decorator that makes sure that a particular attribute in a url
    pattern has been included for this given calling function. This seems
    like a strange problem because Djanog can map urls matchign regexes
    to specific functions, but in our case in Sleepy we map to
    an object for a regular expressiona and we might be more liberal
    in what we accept for a GET call than a POST cal for example
    there might be two regular expressions that point to an endpoin
    /endpoint and /endpoint/(P.*)<entity> and we might require that
    post refers to a given entitity. This is a convenience decorator for
    doing that which hopefully eliminates the length of methods
    """
    def _wrap(fn):
        def _check(*args, **kwargs):
            if param in self.kwargs:
                return fn(*args, **kwargs)
            else:
                return self.json_err(
                    "{0} requests to {1} should contain {2} in the url".format(
                        fn.__name__,
                        self.__class__.__name__,
                        param
                        )
                    )
        return _check
    return _wrap


def ParameterAssert(param, func, description):
    def _wrap(fn):
        def _check(*args, **kwargs):
            if param in self.kwargs and not func(param):
                return self.json_err(
                    "{0} {1}".format(param, description),
                    "Parameter Error"
                    )
            else:
                return fn(*args, **kwargs)
        return _check
    return _wrap

def ParameterType(**types):
    def _wrap(fn):
        def _check(*args, **kwargs):
            try:
                for param, type_ in types.items():
                    kwargs[param] = type_(kwargs[param])
                    if type_ == bool:
                        if kwargs[param].lower() == "true":
                            kwargs[param] = True
                        elif kwargs[param].lower() == "false":
                            kwargs[param] = False
                        else:
                            kwargs[param] = type_(param)

            except KeyError:
                # If there isn't a parameter to type check we assume that the default was declared as
                # a default parameter to the function
                pass

            except ValueError:
                return self.api_error("page_offset parameter must be of type {0}".format(type_))

            return fn(*args, **kwargs)

        return _check
    return _wrap
                                     
def OnlyNewer(get_identifier_func, get_elements_func=None, build_partial_response=None):
    def _wrap(fn):
        def _check(*args, **kwargs):

            def find(needle, seq):
                for ii, elm in enumerate(seq):
                    if elm == needle:
                        return ii, elm
                    return len(seq)

            if "If-Range" in request.META:
                newest_id = request.META["If-Range"]

                # If we dont' override the way we handle responses assume they're the normal
                # json responses with data as one of the top elements
                if not get_elements_func:
                    get_elements_func = lambda resp: json.loads(resp)["data"]

                    if not build_partial_response:
                        build_partial_response = lambda elements: kwargs["self"].api_out(elements)

                    response = fn(*args, **kwargs)
                    elements = get_elements_func(response)
                    elements = elements[:find(newest_id, get_identifier_func)]
                    return build_partial_response(elements)

        return _check
    return _wrap

            
    
