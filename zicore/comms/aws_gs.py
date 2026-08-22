"""
ZICORE ZSRI — AWS Ground Station adapter.

Real connector to the AWS Ground Station service (LEO/MEO antennas as a
service, billed per contact minute). Uses the AWS SDK for Python (boto3),
which is an OPTIONAL dependency: if boto3 is not installed, or no AWS
credentials are configured, the provider reports available=False and all
calls degrade gracefully (no crash, no secrets logged).

Credentials come ONLY from the standard AWS environment variables
(AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION / AWS_PROFILE).

Real AWS Ground Station flow::

    reserve_contact(missionProfileArn, satelliteArn, startTime, endTime)
    get_satellite / list_configs / create_config / create_dataflow_endpoint_group
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from .providers import SEGMENT_LEO, SpaceProvider, register_provider

def _aws_error(reason: str) -> Dict:
    return {
        "provider": "aws-gs",
        "status": "degraded",
        "available": False,
        "reason": reason,
        "latency_ms": None,
    }


class AWSGroundStationProvider(SpaceProvider):
    id = "aws-gs"
    name = "AWS Ground Station"
    segment = SEGMENT_LEO
    bands = ["S", "X", "Ka"]
    api_base = "https://groundstation.{region}.amazonaws.com"

    def __init__(self) -> None:
        self._client = None
        self._boto3 = None
        try:
            import boto3  # type: ignore

            self._boto3 = boto3
        except ImportError:
            self._boto3 = None

    # -- helpers ----------------------------------------------------------
    def _make_client(self):
        if self._client is not None:
            return self._client
        if self._boto3 is None:
            return None
        try:
            self._client = self._boto3.client("groundstation", region_name="us-west-2")
        except Exception:
            self._client = None
        return self._client

    # -- interface --------------------------------------------------------
    def describe(self) -> Dict:
        d = super().describe()
        d["available"] = self._boto3 is not None
        d["reason"] = None if d["available"] else "boto3 not installed (pip install boto3)"
        return d

    def health(self) -> Dict:
        d = self.describe()
        if self._boto3 is None:
            return {**d, "status": "degraded", "latency_ms": None}
        try:
            sts = self._boto3.client("sts", region_name="us-west-2")
            t0 = time.monotonic()
            ident = sts.get_caller_identity()
            return {**d, "status": "ok",
                    "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                    "identity": ident.get("Arn", "")}
        except Exception as e:
            msg = str(e)
            return {**d, "status": "degraded", "latency_ms": None,
                    "reason": "AWS credentials not configured or invalid: " + msg[:160]}

    def list_stations(self) -> List[Dict]:
        d = self.describe()
        if not d["available"]:
            return [{"provider": self.id, "available": False, "reason": d["reason"]}]
        client = self._make_client()
        if client is None:
            return [{"provider": self.id, "available": False, "reason": "AWS credentials missing"}]
        try:
            sat = client.list_satellites()
            return [{"provider": self.id, "available": True, "satellites": sat.get("satellites", [])}]
        except Exception as e:
            return [{"provider": self.id, "available": False, "reason": str(e)[:200]}]

    def schedule_contact(self, **kwargs) -> Dict:
        client = self._make_client()
        if client is None:
            return _aws_error("boto3/credentials not available")
        try:
            resp = client.reserve_contact(
                missionProfileArn=str(kwargs.get("missionProfileArn", "")),
                satelliteArn=str(kwargs.get("satelliteArn", "")),
                startTime=kwargs.get("startTime"),
                endTime=kwargs.get("endTime"),
            )
            return {"provider": self.id, "status": "ok",
                    "contact_id": resp.get("contactId")}
        except Exception as e:
            return _aws_error(str(e)[:200])


def _register_aws() -> AWSGroundStationProvider:
    return AWSGroundStationProvider()


register_provider(AWSGroundStationProvider())
