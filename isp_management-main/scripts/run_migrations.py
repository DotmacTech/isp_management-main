#!/usr/bin/env python
"""
Script to run database migrations for the ISP Management Platform.

This script uses Alembic to run database migrations, ensuring that the database schema
is up-to-date with the latest changes.

Usage:
    python run_migrations.py [--revision REVISION] [--downgrade]

Options:
    --revision REVISION    Specific revision to migrate to
    --downgrade           Downgrade to the previous revision
"""

import os
import sys
import argparse
import logging
from alembic import command
from alembic.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_migrations")

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Set up Alembic configuration
alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
alembic_cfg.set_main_option("script_location", os.path.join(project_root, "migrations"))


def run_migrations(revision=None, downgrade=False):
    """Run database migrations."""
    try:
        if downgrade:
            if revision:
                logger.info(f"Downgrading database to revision: {revision}")
                command.downgrade(alembic_cfg, revision)
            else:
                logger.info("Downgrading database to previous revision")
                command.downgrade(alembic_cfg, "-1")
        else:
            if revision:
                logger.info(f"Upgrading database to revision: {revision}")
                command.upgrade(alembic_cfg, revision)
            else:
                logger.info("Upgrading database to latest revision")
                command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running database migration: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--revision", help="Specific revision to migrate to")
    parser.add_argument("--downgrade", action="store_true", help="Downgrade to the previous revision")
    args = parser.parse_args()
    
    success = run_migrations(args.revision, args.downgrade)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
