"""
ZICORE ZSRI — Space Communications Network.

Ground-segment-as-a-service (GSaaS) facade: KSAT, Leaf Space, SSC, AWS
Ground Station and future commercial lunar relays (NASA LCRNS / Intuitive
Machines) exposed as ONE space network to ZIO and Mission Control.

Public API::

    from zicore.comms import SpaceNetwork
    net = SpaceNetwork()
    net.providers()            # all providers + health
    net.network()              # layered map LEO->Gateway->Relay->Luna
    net.link_budget(band="X", distance_km=384400)
    net.earth_moon_status()    # distance + light-time now/perigee/apogee
"""

from .network import SpaceNetwork

__all__ = ["SpaceNetwork"]
