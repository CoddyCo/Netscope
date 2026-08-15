"""
DynamoDB Client for NetScope Trace Persistence
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Handles persistence of network traces to AWS DynamoDB."""

    def __init__(self, table_name: str = "NetscopeTraces"):
        self.table_name = table_name
        self.dynamodb = None
        self.table = None

        if HAS_BOTO3:
            try:
                self.dynamodb = boto3.resource("dynamodb", region_name="eu-north-1")
                self.table = self.dynamodb.Table(self.table_name)
            except Exception as e:
                logger.warning(f"Failed to initialize boto3 DynamoDB client: {e}")

    def save_trace(self, target: str, ip: str, timestamp: str, latency: float) -> bool:
        """
        Saves basic trace metrics to DynamoDB.
        Fails silently if AWS credentials are not configured.
        """
        if not self.table:
            return False

        try:
            self.table.put_item(
                Item={
                    "Target": target,
                    "Timestamp": timestamp,
                    "ResolvedIP": ip,
                    "AvgLatency": str(latency),
                }
            )
            return True
        except (BotoCoreError, ClientError) as e:
            logger.debug(f"Silently ignoring DynamoDB upload failure: {e}")
            return False

    def get_historical_average_latency(self, target: str) -> Optional[float]:
        """
        Queries DynamoDB for the historical average latency of a target.
        """
        if not self.table:
            return None

        try:
            from boto3.dynamodb.conditions import Key
            
            response = self.table.query(
                KeyConditionExpression=Key("Target").eq(target)
            )
            
            items = response.get("Items", [])
            if not items:
                return None
                
            latencies = []
            for item in items:
                if "AvgLatency" in item:
                    try:
                        latencies.append(float(item["AvgLatency"]))
                    except ValueError:
                        pass
                        
            if not latencies:
                return None
                
            return sum(latencies) / len(latencies)
            
        except (BotoCoreError, ClientError) as e:
            logger.debug(f"Silently ignoring DynamoDB query failure: {e}")
            return None
