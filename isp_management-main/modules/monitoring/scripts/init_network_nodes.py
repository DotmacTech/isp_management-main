#!/usr/bin/env python
"""
Initialize Default Network Nodes

This script initializes the default network nodes in the database
based on the configuration in network_monitoring.py.
"""

import sys
import os
import logging
from sqlalchemy.orm import Session

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from modules.core.database import get_db, engine, Base
from modules.monitoring.models import NetworkNode, NodeType
from modules.monitoring.config.network_monitoring import DEFAULT_NETWORK_NODES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def init_network_nodes():
    """
    Initialize default network nodes in the database.
    
    This function checks if each default network node exists in the database,
    and if not, creates it.
    """
    logger.info("Initializing default network nodes...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Iterate through default network nodes
        for node_data in DEFAULT_NETWORK_NODES:
            # Check if node already exists
            existing_node = db.query(NetworkNode).filter(NetworkNode.id == node_data['id']).first()
            
            if existing_node:
                logger.info(f"Network node '{node_data['name']}' already exists, skipping...")
                continue
            
            # Convert string type to enum
            node_type_str = node_data.pop('type', 'other')
            try:
                node_type = NodeType(node_type_str)
            except ValueError:
                logger.warning(f"Invalid node type '{node_type_str}', using 'other' instead")
                node_type = NodeType.OTHER
            
            # Create new network node
            new_node = NetworkNode(
                **node_data,
                type=node_type
            )
            
            # Add to database
            db.add(new_node)
            logger.info(f"Added network node '{node_data['name']}' to database")
        
        # Commit changes
        db.commit()
        logger.info("Default network nodes initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing default network nodes: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_network_nodes()
