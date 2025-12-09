import dramatiq
from .services import promote_asset

@dramatiq.actor
def async_promote_asset(asset_id, from_env, to_env, user_id):
    """
    Promote asset asynchronously using Dramatiq worker.
    """
    promote_asset(asset_id, from_env, to_env, user_id)
