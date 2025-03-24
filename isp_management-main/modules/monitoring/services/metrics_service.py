"""
Service for managing system metrics in the monitoring module.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from redis import Redis

from modules.monitoring.models.system_metric import SystemMetric, MetricType
from modules.monitoring.schemas.system_metric import (
    SystemMetricCreate, SystemMetricResponse, SystemMetricSummary,
    SystemMetricAggregation, SystemMetricFilter
)
from modules.monitoring.schemas.dashboard import PaginatedResponse
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class MetricsService:
    """Service for managing system metrics in the monitoring module."""

    def __init__(self, db: Session, redis: Optional[Redis] = None):
        """Initialize the service with database session and Redis client."""
        self.db = db
        self.redis = redis
        self.es_client = ElasticsearchClient()

    def create_metric(self, metric_data: SystemMetricCreate) -> SystemMetric:
        """
        Record a new system metric.
        
        Args:
            metric_data: Metric data to record.
            
        Returns:
            Created metric.
        """
        metric = SystemMetric(**metric_data.model_dump())
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        
        # Cache latest metric in Redis if available
        if self.redis:
            cache_key = f"metric:{metric.service_name}:{metric.host_name}:{metric.metric_type.value}"
            self.redis.set(cache_key, json.dumps(metric.model_dump()), ex=3600)  # 1 hour expiry
        
        return metric

    def search_metrics(
        self,
        service_names: Optional[List[str]] = None,
        host_names: Optional[List[str]] = None,
        metric_types: Optional[List[MetricType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        aggregation: Optional[str] = None,
        group_by: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Union[PaginatedResponse[SystemMetricResponse], List[SystemMetricAggregation]]:
        """
        Search metrics with filtering and optional aggregation.
        
        Args:
            service_names: Filter by service names.
            host_names: Filter by host names.
            metric_types: Filter by metric types.
            start_time: Filter by start time.
            end_time: Filter by end time.
            tags: Filter by tags.
            aggregation: Aggregation function (avg, sum, min, max, count).
            group_by: Fields to group by for aggregation.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            List of metrics or aggregations.
        """
        # Use Elasticsearch if connected and no aggregation is needed
        if self.es_client.is_connected() and not aggregation:
            return self._search_metrics_elasticsearch(
                service_names, host_names, metric_types, start_time, end_time,
                tags, offset, limit
            )
        
        # Build query
        query = self.db.query(SystemMetric)
        
        if service_names:
            query = query.filter(SystemMetric.service_name.in_(service_names))
        
        if host_names:
            query = query.filter(SystemMetric.host_name.in_(host_names))
        
        if metric_types:
            query = query.filter(SystemMetric.metric_type.in_(metric_types))
        
        if start_time:
            query = query.filter(SystemMetric.timestamp >= start_time)
        
        if end_time:
            query = query.filter(SystemMetric.timestamp <= end_time)
        
        if tags:
            for tag in tags:
                query = query.filter(SystemMetric.tags.contains(tag))
        
        # Handle aggregation
        if aggregation and group_by:
            return self._aggregate_metrics(query, aggregation, group_by)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        metrics = query.order_by(desc(SystemMetric.timestamp)).offset(offset).limit(limit).all()
        
        # Create paginated response
        return PaginatedResponse[SystemMetricResponse](
            items=[SystemMetricResponse.from_orm(metric) for metric in metrics],
            total=total,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

    def _search_metrics_elasticsearch(
        self,
        service_names: Optional[List[str]] = None,
        host_names: Optional[List[str]] = None,
        metric_types: Optional[List[MetricType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[SystemMetricResponse]:
        """
        Search metrics using Elasticsearch.
        
        Args:
            service_names: Filter by service names.
            host_names: Filter by host names.
            metric_types: Filter by metric types.
            start_time: Filter by start time.
            end_time: Filter by end time.
            tags: Filter by tags.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Paginated response with metrics.
        """
        # Build Elasticsearch query
        query = {"bool": {"must": []}}
        
        if service_names:
            query["bool"]["must"].append({"terms": {"service_name.keyword": service_names}})
        
        if host_names:
            query["bool"]["must"].append({"terms": {"host_name.keyword": host_names}})
        
        if metric_types:
            query["bool"]["must"].append({"terms": {"metric_type.keyword": [mt.value for mt in metric_types]}})
        
        if start_time or end_time:
            range_query = {"range": {"timestamp": {}}}
            if start_time:
                range_query["range"]["timestamp"]["gte"] = start_time.isoformat()
            if end_time:
                range_query["range"]["timestamp"]["lte"] = end_time.isoformat()
            query["bool"]["must"].append(range_query)
        
        if tags:
            for tag in tags:
                query["bool"]["must"].append({"term": {"tags": tag}})
        
        # Execute search
        result = self.es_client.search(
            index="system_metrics",
            query=query,
            sort=[{"timestamp": {"order": "desc"}}],
            from_=offset,
            size=limit
        )
        
        # Process results
        metrics = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            metrics.append(SystemMetricResponse(**source))
        
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        return PaginatedResponse[SystemMetricResponse](
            items=metrics,
            total=total,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

    def _aggregate_metrics(
        self,
        query,
        aggregation: str,
        group_by: List[str]
    ) -> List[SystemMetricAggregation]:
        """
        Aggregate metrics.
        
        Args:
            query: SQLAlchemy query.
            aggregation: Aggregation function (avg, sum, min, max, count).
            group_by: Fields to group by.
            
        Returns:
            List of aggregated metrics.
        """
        # Select group by columns
        group_columns = []
        for field in group_by:
            if hasattr(SystemMetric, field):
                group_columns.append(getattr(SystemMetric, field))
        
        # Select aggregation function
        if aggregation == "avg":
            agg_func = func.avg(SystemMetric.value)
        elif aggregation == "sum":
            agg_func = func.sum(SystemMetric.value)
        elif aggregation == "min":
            agg_func = func.min(SystemMetric.value)
        elif aggregation == "max":
            agg_func = func.max(SystemMetric.value)
        elif aggregation == "count":
            agg_func = func.count(SystemMetric.id)
        else:
            raise ValueError(f"Invalid aggregation function: {aggregation}")
        
        # Execute query
        result = query.with_entities(*group_columns, agg_func).group_by(*group_columns).all()
        
        # Format result
        aggregations = []
        for row in result:
            agg = {"value": row[-1]}
            for i, field in enumerate(group_by):
                agg[field] = row[i]
            aggregations.append(SystemMetricAggregation(**agg))
        
        return aggregations

    def get_latest_metrics(
        self,
        service_name: Optional[str] = None,
        host_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None
    ) -> List[SystemMetricResponse]:
        """
        Get the latest metrics, optionally filtered by service, host, or metric type.
        
        Args:
            service_name: Filter by service name.
            host_name: Filter by host name.
            metric_type: Filter by metric type.
            
        Returns:
            List of latest metrics.
        """
        # Try to get from Redis cache first
        if self.redis and service_name and host_name and metric_type:
            cache_key = f"metric:{service_name}:{host_name}:{metric_type.value}"
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    return [SystemMetricResponse(**json.loads(cached))]
                except Exception as e:
                    logger.warning(f"Error parsing cached metric: {e}")
        
        # Build subquery to get the latest timestamp for each service/host/metric combination
        subquery = self.db.query(
            SystemMetric.service_name,
            SystemMetric.host_name,
            SystemMetric.metric_type,
            func.max(SystemMetric.timestamp).label("max_timestamp")
        )
        
        if service_name:
            subquery = subquery.filter(SystemMetric.service_name == service_name)
        
        if host_name:
            subquery = subquery.filter(SystemMetric.host_name == host_name)
        
        if metric_type:
            subquery = subquery.filter(SystemMetric.metric_type == metric_type)
        
        subquery = subquery.group_by(
            SystemMetric.service_name,
            SystemMetric.host_name,
            SystemMetric.metric_type
        ).subquery()
        
        # Join with the main table to get the full records
        query = self.db.query(SystemMetric).join(
            subquery,
            and_(
                SystemMetric.service_name == subquery.c.service_name,
                SystemMetric.host_name == subquery.c.host_name,
                SystemMetric.metric_type == subquery.c.metric_type,
                SystemMetric.timestamp == subquery.c.max_timestamp
            )
        )
        
        metrics = query.all()
        
        return [SystemMetricResponse.from_orm(metric) for metric in metrics]

    def get_metric_trends(
        self,
        service_name: str,
        host_name: str,
        metric_type: MetricType,
        hours: int = 24
    ) -> List[SystemMetricResponse]:
        """
        Get metric trends over time for a specific service, host, and metric type.
        
        Args:
            service_name: Service name.
            host_name: Host name.
            metric_type: Metric type.
            hours: Number of hours to look back.
            
        Returns:
            List of metrics over time.
        """
        # Calculate start time
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query metrics
        metrics = self.db.query(SystemMetric).filter(
            SystemMetric.service_name == service_name,
            SystemMetric.host_name == host_name,
            SystemMetric.metric_type == metric_type,
            SystemMetric.timestamp >= start_time
        ).order_by(SystemMetric.timestamp).all()
        
        return [SystemMetricResponse.from_orm(metric) for metric in metrics]

    def get_metrics_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, SystemMetricSummary]:
        """
        Get a summary of system metrics.
        
        Args:
            start_time: Start time for the summary.
            end_time: End time for the summary.
            
        Returns:
            Dictionary of metric summaries by metric type.
        """
        # Build query
        query = self.db.query(SystemMetric)
        
        if start_time:
            query = query.filter(SystemMetric.timestamp >= start_time)
        
        if end_time:
            query = query.filter(SystemMetric.timestamp <= end_time)
        
        # Group by metric type
        result = query.with_entities(
            SystemMetric.metric_type,
            func.min(SystemMetric.value).label("min_value"),
            func.max(SystemMetric.value).label("max_value"),
            func.avg(SystemMetric.value).label("avg_value"),
            func.count(SystemMetric.id).label("count")
        ).group_by(SystemMetric.metric_type).all()
        
        # Format result
        summaries = {}
        for row in result:
            metric_type, min_value, max_value, avg_value, count = row
            summaries[metric_type.value] = SystemMetricSummary(
                metric_type=metric_type,
                min_value=min_value,
                max_value=max_value,
                avg_value=avg_value,
                count=count
            )
        
        return summaries

    def sync_metrics_to_elasticsearch(self, limit: int = 100) -> int:
        """
        Sync unsynced metrics to Elasticsearch.
        
        Args:
            limit: Maximum number of metrics to sync.
            
        Returns:
            Number of metrics synced.
        """
        if not self.es_client.is_connected():
            logger.warning("Elasticsearch is not connected, skipping sync")
            return 0
        
        # Get unsynced metrics
        metrics = self.db.query(SystemMetric).filter(
            SystemMetric.elasticsearch_synced == False
        ).limit(limit).all()
        
        if not metrics:
            return 0
        
        # Prepare bulk data
        bulk_data = []
        for metric in metrics:
            bulk_data.append({
                "_index": "system_metrics",
                "_id": metric.id,
                "_source": metric.model_dump()
            })
        
        # Bulk index to Elasticsearch
        success_count = self.es_client.bulk_index(bulk_data)
        
        # Mark metrics as synced
        for metric in metrics[:success_count]:
            metric.elasticsearch_synced = True
        
        self.db.commit()
        
        return success_count
