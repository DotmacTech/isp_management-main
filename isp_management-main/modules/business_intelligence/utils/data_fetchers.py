"""
Data fetchers for the Business Intelligence and Reporting module.

This module provides classes for fetching data from different sources for report generation.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
import asyncio
from datetime import datetime, timedelta
import aiohttp
import sqlalchemy
from sqlalchemy import text

from backend_core.database import get_db_session
from backend_core.services.redis_client import RedisClient
from backend_core.services.elasticsearch_client import ElasticsearchClient
from ..models.report import DataSource

logger = logging.getLogger(__name__)


class DataFetcher:
    """Class for fetching data from various sources."""
    
    async def fetch_data(
        self, 
        query_definition: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_sources: List[DataSource]
    ) -> Dict[str, Any]:
        """
        Fetch data for a report based on the query definition.
        
        Args:
            query_definition: Definition of the queries to execute
            parameters: Parameters to apply to the queries
            data_sources: Available data sources
            
        Returns:
            Dictionary containing the fetched data
        """
        result = {}
        
        # Process each query defined in the query definition
        queries = query_definition.get('queries', [])
        for query in queries:
            query_id = query.get('id')
            query_type = query.get('type')
            data_source_id = query.get('data_source_id')
            
            # Find the data source
            data_source = next((ds for ds in data_sources if ds.id == data_source_id), None)
            if not data_source:
                logger.warning(f"Data source {data_source_id} not found for query {query_id}")
                continue
            
            # Fetch data based on query type
            try:
                if query_type == 'sql':
                    data = await self._fetch_sql_data(query, parameters, data_source)
                elif query_type == 'elasticsearch':
                    data = await self._fetch_elasticsearch_data(query, parameters, data_source)
                elif query_type == 'redis':
                    data = await self._fetch_redis_data(query, parameters, data_source)
                elif query_type == 'api':
                    data = await self._fetch_api_data(query, parameters, data_source)
                elif query_type == 'file':
                    data = await self._fetch_file_data(query, parameters, data_source)
                else:
                    logger.warning(f"Unsupported query type: {query_type}")
                    continue
                
                # Apply transformations if defined
                transformations = query.get('transformations', [])
                if transformations:
                    data = self._apply_transformations(data, transformations, parameters)
                
                # Add to result
                result[query_id] = data
            
            except Exception as e:
                logger.exception(f"Error fetching data for query {query_id}: {str(e)}")
                result[query_id] = {'error': str(e)}
        
        return result

    async def _fetch_sql_data(
        self, 
        query: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_source: DataSource
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from a SQL database.
        
        Args:
            query: Query definition
            parameters: Parameters to apply to the query
            data_source: Data source configuration
            
        Returns:
            List of dictionaries containing the query results
        """
        sql_query = query.get('sql')
        if not sql_query:
            raise ValueError("SQL query not defined")
        
        # Apply parameters to the query
        if parameters:
            sql_query = self._apply_parameters_to_sql(sql_query, parameters)
        
        # Get connection details
        connection_details = data_source.connection_details
        
        # For internal database, use the existing session
        if connection_details.get('internal', False):
            with get_db_session() as db:
                result = db.execute(text(sql_query))
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result]
        
        # For external database, create a new connection
        else:
            engine = sqlalchemy.create_engine(connection_details.get('connection_string'))
            with engine.connect() as connection:
                result = connection.execute(text(sql_query))
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result]

    async def _fetch_elasticsearch_data(
        self, 
        query: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_source: DataSource
    ) -> Dict[str, Any]:
        """
        Fetch data from Elasticsearch.
        
        Args:
            query: Query definition
            parameters: Parameters to apply to the query
            data_source: Data source configuration
            
        Returns:
            Dictionary containing the query results
        """
        es_query = query.get('elasticsearch_query')
        if not es_query:
            raise ValueError("Elasticsearch query not defined")
        
        # Apply parameters to the query
        if parameters:
            es_query = self._apply_parameters_to_json(es_query, parameters)
        
        # Get connection details
        connection_details = data_source.connection_details
        
        # For internal Elasticsearch, use the existing client
        if connection_details.get('internal', False):
            es_client = ElasticsearchClient()
        else:
            # Create a new client with custom configuration
            es_client = ElasticsearchClient(
                hosts=connection_details.get('hosts'),
                username=connection_details.get('username'),
                password=connection_details.get('password')
            )
        
        # Execute query
        index = query.get('index')
        result = await es_client.search(index, es_query)
        
        return result

    async def _fetch_redis_data(
        self, 
        query: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_source: DataSource
    ) -> Any:
        """
        Fetch data from Redis.
        
        Args:
            query: Query definition
            parameters: Parameters to apply to the query
            data_source: Data source configuration
            
        Returns:
            Data from Redis
        """
        key = query.get('key')
        if not key:
            raise ValueError("Redis key not defined")
        
        # Apply parameters to the key
        if parameters:
            key = self._apply_parameters_to_string(key, parameters)
        
        # Get connection details
        connection_details = data_source.connection_details
        
        # For internal Redis, use the existing client
        if connection_details.get('internal', False):
            redis_client = RedisClient()
        else:
            # Create a new client with custom configuration
            redis_client = RedisClient(
                host=connection_details.get('host'),
                port=connection_details.get('port'),
                password=connection_details.get('password'),
                db=connection_details.get('db', 0)
            )
        
        # Get data from Redis
        data = await redis_client.get(key)
        
        # Parse JSON if needed
        if query.get('parse_json', False) and data:
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Redis data as JSON: {data}")
        
        return data

    async def _fetch_api_data(
        self, 
        query: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_source: DataSource
    ) -> Dict[str, Any]:
        """
        Fetch data from an API.
        
        Args:
            query: Query definition
            parameters: Parameters to apply to the query
            data_source: Data source configuration
            
        Returns:
            Dictionary containing the API response
        """
        url = query.get('url')
        if not url:
            raise ValueError("API URL not defined")
        
        # Apply parameters to the URL
        if parameters:
            url = self._apply_parameters_to_string(url, parameters)
        
        # Get connection details
        connection_details = data_source.connection_details
        
        # Prepare headers
        headers = connection_details.get('headers', {})
        if 'authorization' in connection_details:
            headers['Authorization'] = connection_details['authorization']
        
        # Prepare request
        method = query.get('method', 'GET')
        request_data = query.get('data')
        
        # Apply parameters to request data
        if parameters and request_data:
            request_data = self._apply_parameters_to_json(request_data, parameters)
        
        # Execute request
        async with aiohttp.ClientSession() as session:
            if method.upper() == 'GET':
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise ValueError(f"API request failed with status {response.status}")
                    return await response.json()
            elif method.upper() == 'POST':
                async with session.post(url, headers=headers, json=request_data) as response:
                    if response.status != 200:
                        raise ValueError(f"API request failed with status {response.status}")
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

    async def _fetch_file_data(
        self, 
        query: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        data_source: DataSource
    ) -> Any:
        """
        Fetch data from a file.
        
        Args:
            query: Query definition
            parameters: Parameters to apply to the query
            data_source: Data source configuration
            
        Returns:
            Data from the file
        """
        file_path = query.get('file_path')
        if not file_path:
            raise ValueError("File path not defined")
        
        # Apply parameters to the file path
        if parameters:
            file_path = self._apply_parameters_to_string(file_path, parameters)
        
        # Get file format
        file_format = query.get('format', 'json')
        
        # Read file
        with open(file_path, 'r') as f:
            if file_format == 'json':
                return json.load(f)
            elif file_format == 'csv':
                import pandas as pd
                return pd.read_csv(file_path).to_dict(orient='records')
            elif file_format == 'excel':
                import pandas as pd
                return pd.read_excel(file_path).to_dict(orient='records')
            else:
                return f.read()

    def _apply_parameters_to_sql(
        self, sql_query: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Apply parameters to a SQL query.
        
        Args:
            sql_query: SQL query
            parameters: Parameters to apply
            
        Returns:
            SQL query with parameters applied
        """
        # Simple string replacement for parameters
        for key, value in parameters.items():
            placeholder = f":{key}"
            if isinstance(value, str):
                # Escape single quotes in string values
                value = value.replace("'", "''")
                value = f"'{value}'"
            elif value is None:
                value = "NULL"
            sql_query = sql_query.replace(placeholder, str(value))
        
        return sql_query

    def _apply_parameters_to_json(
        self, json_obj: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply parameters to a JSON object.
        
        Args:
            json_obj: JSON object
            parameters: Parameters to apply
            
        Returns:
            JSON object with parameters applied
        """
        # Convert to string
        json_str = json.dumps(json_obj)
        
        # Apply parameters
        json_str = self._apply_parameters_to_string(json_str, parameters)
        
        # Convert back to object
        return json.loads(json_str)

    def _apply_parameters_to_string(
        self, string: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Apply parameters to a string.
        
        Args:
            string: String to modify
            parameters: Parameters to apply
            
        Returns:
            String with parameters applied
        """
        for key, value in parameters.items():
            placeholder = f":{key}"
            string = string.replace(placeholder, str(value))
        
        return string

    def _apply_transformations(
        self, 
        data: Any, 
        transformations: List[Dict[str, Any]],
        parameters: Optional[Dict[str, Any]]
    ) -> Any:
        """
        Apply transformations to data.
        
        Args:
            data: Data to transform
            transformations: List of transformations to apply
            parameters: Parameters for transformations
            
        Returns:
            Transformed data
        """
        # Process each transformation in order
        for transformation in transformations:
            transform_type = transformation.get('type')
            
            if transform_type == 'filter':
                data = self._apply_filter_transformation(data, transformation, parameters)
            elif transform_type == 'sort':
                data = self._apply_sort_transformation(data, transformation)
            elif transform_type == 'group':
                data = self._apply_group_transformation(data, transformation)
            elif transform_type == 'aggregate':
                data = self._apply_aggregate_transformation(data, transformation)
            elif transform_type == 'limit':
                data = self._apply_limit_transformation(data, transformation)
            elif transform_type == 'map':
                data = self._apply_map_transformation(data, transformation)
            elif transform_type == 'flatten':
                data = self._apply_flatten_transformation(data, transformation)
            elif transform_type == 'join':
                data = self._apply_join_transformation(data, transformation)
            else:
                logger.warning(f"Unsupported transformation type: {transform_type}")
        
        return data

    def _apply_filter_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any],
        parameters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply filter transformation."""
        if not isinstance(data, list):
            return data
        
        conditions = transformation.get('conditions', [])
        if not conditions:
            return data
        
        result = []
        for item in data:
            if self._evaluate_conditions(item, conditions, parameters):
                result.append(item)
        
        return result

    def _apply_sort_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply sort transformation."""
        if not isinstance(data, list):
            return data
        
        sort_by = transformation.get('sort_by')
        if not sort_by:
            return data
        
        reverse = transformation.get('reverse', False)
        
        return sorted(data, key=lambda x: x.get(sort_by), reverse=reverse)

    def _apply_group_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Apply group transformation."""
        if not isinstance(data, list):
            return data
        
        group_by = transformation.get('group_by')
        if not group_by:
            return data
        
        result = {}
        for item in data:
            key = item.get(group_by)
            if key not in result:
                result[key] = []
            result[key].append(item)
        
        return result

    def _apply_aggregate_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply aggregate transformation."""
        # Implementation omitted for brevity
        return data

    def _apply_limit_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply limit transformation."""
        if not isinstance(data, list):
            return data
        
        limit = transformation.get('limit')
        if not limit:
            return data
        
        return data[:limit]

    def _apply_map_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply map transformation."""
        if not isinstance(data, list):
            return data
        
        mappings = transformation.get('mappings', {})
        if not mappings:
            return data
        
        result = []
        for item in data:
            new_item = {}
            for new_key, old_key in mappings.items():
                if old_key in item:
                    new_item[new_key] = item[old_key]
            result.append(new_item)
        
        return result

    def _apply_flatten_transformation(
        self, 
        data: Dict[str, List[Dict[str, Any]]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply flatten transformation."""
        if not isinstance(data, dict):
            return data
        
        result = []
        for key, items in data.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item_copy = item.copy()
                        item_copy['_group'] = key
                        result.append(item_copy)
        
        return result

    def _apply_join_transformation(
        self, 
        data: List[Dict[str, Any]], 
        transformation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply join transformation."""
        # Implementation omitted for brevity
        return data

    def _evaluate_conditions(
        self, 
        item: Dict[str, Any], 
        conditions: List[Dict[str, Any]],
        parameters: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Evaluate filter conditions for an item.
        
        Args:
            item: Item to evaluate
            conditions: List of conditions
            parameters: Parameters for conditions
            
        Returns:
            True if all conditions are met, False otherwise
        """
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            # Apply parameters to value if it's a parameter reference
            if isinstance(value, str) and value.startswith(':') and parameters:
                param_name = value[1:]
                if param_name in parameters:
                    value = parameters[param_name]
            
            # Get field value
            field_value = item.get(field)
            
            # Evaluate condition
            if operator == 'eq' and field_value != value:
                return False
            elif operator == 'ne' and field_value == value:
                return False
            elif operator == 'gt' and not (field_value > value):
                return False
            elif operator == 'lt' and not (field_value < value):
                return False
            elif operator == 'gte' and not (field_value >= value):
                return False
            elif operator == 'lte' and not (field_value <= value):
                return False
            elif operator == 'in' and field_value not in value:
                return False
            elif operator == 'nin' and field_value in value:
                return False
            elif operator == 'contains' and not (isinstance(field_value, str) and value in field_value):
                return False
            elif operator == 'starts_with' and not (isinstance(field_value, str) and field_value.startswith(value)):
                return False
            elif operator == 'ends_with' and not (isinstance(field_value, str) and field_value.endswith(value)):
                return False
        
        return True
