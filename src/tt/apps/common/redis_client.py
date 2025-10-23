import logging
import redis

from django.conf import settings

logger = logging.getLogger(__name__)

# We want to allow running without the redis dependency, so it is not
# enough to see a "None" for the client to know whether we tried to
# initialize the client or not.
#
_g_global_redis_initialized_attempted = False

# According to docs, the Redis client is thread safe.
#
_g_global_redis_client = None


def initialize_global_cache_client():
    """
    Need to call this once at process start if you want to use cache-based
    features.
    """
    global _g_global_redis_initialized_attempted
    global _g_global_redis_client

    if _g_global_redis_initialized_attempted:
        return
    _g_global_redis_initialized_attempted = True
    
    if _g_global_redis_client:
        _g_global_redis_client = None  # No good way to explicitly "close" this

    host, port = ( settings.REDIS_HOST, settings.REDIS_PORT )
    if not port:
        port = 6379

    logger.info( "Attempting to connect to Redis at %s:%s ..." % ( host, port ))

    try:
        _g_global_redis_client = redis.StrictRedis( host = host,
                                                    port = port,
                                                    db = 0,
                                                    socket_timeout = 5,
                                                    socket_connect_timeout = 5,
                                                    decode_responses = True )
        _g_global_redis_client.ping()
        logger.info( "Successfully connected to Redis at %s:%s" % ( host, port ))
        
    except ( ConnectionRefusedError, redis.exceptions.ConnectionError ) as e:
        logger.error( f'Could not connect to Redis server: {e}' )
        _g_global_redis_client = None
    except ValueError as ve:
        logger.exception( f'Problem seting up Redis client: {ve}' )
        _g_global_redis_client = None
        
    return


def exists_redis_client():
    if not _g_global_redis_client:
        initialize_global_cache_client()
    return _g_global_redis_client is not None
       

def get_redis_client():
    if not _g_global_redis_client:
        initialize_global_cache_client()
    return _g_global_redis_client


def clear_redis_client():
    global _g_global_redis_client_initialized
    global _g_global_redis_client
    if _g_global_redis_client:
        logger.info( "Clearing existing Redis connection" )
        _g_global_redis_client_initialized = False
        _g_global_redis_client = None  # No good way to explicitly "close" this
    return


class CacheNotAvailableError(Exception):
    pass


    
