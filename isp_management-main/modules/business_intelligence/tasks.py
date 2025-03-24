"""
Celery tasks for the Business Intelligence and Reporting module.

This module provides Celery tasks for scheduled report generation and other
background tasks related to the Business Intelligence module.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os

from celery import shared_task
from sqlalchemy.orm import Session

from backend_core.database import get_db_session
from backend_core.services.redis_client import RedisClient
from backend_core.services.notification_service import NotificationService
from .services.report_service import ReportService
from .services.report_scheduling_service import ReportSchedulingService
from .services.report_execution_service import ReportExecutionService
from .models.report import ScheduledReport, ReportExecution, ReportExecutionStatus
from .schemas.report import ReportExecutionCreate

logger = logging.getLogger(__name__)

# Initialize services
report_service = ReportService()
report_scheduling_service = ReportSchedulingService(report_service)
report_execution_service = ReportExecutionService(report_service)
notification_service = NotificationService()
redis_client = RedisClient()


@shared_task(name="business_intelligence.check_scheduled_reports")
def check_scheduled_reports() -> Dict[str, Any]:
    """
    Check for scheduled reports that need to be executed.
    
    This task is scheduled to run periodically (e.g., every minute) to check for
    scheduled reports that need to be executed based on their schedule.
    
    Returns:
        Dictionary with execution results
    """
    logger.info("Checking for scheduled reports to execute")
    
    result = {
        "scheduled_reports_checked": 0,
        "reports_executed": 0,
        "errors": 0
    }
    
    try:
        with get_db_session() as db:
            # Get all active scheduled reports
            scheduled_reports = report_scheduling_service.get_due_scheduled_reports(db)
            result["scheduled_reports_checked"] = len(scheduled_reports)
            
            # Execute each due report
            for scheduled_report in scheduled_reports:
                try:
                    # Create execution data
                    execution_data = ReportExecutionCreate(
                        template_id=scheduled_report.template_id,
                        parameters=scheduled_report.parameters,
                        scheduled_report_id=scheduled_report.id
                    )
                    
                    # Execute report
                    execution = report_execution_service.execute_report(
                        db, execution_data, scheduled_report.owner_id
                    )
                    
                    # Update next execution time
                    report_scheduling_service.update_next_execution_time(
                        db, scheduled_report.id
                    )
                    
                    # Queue the report processing task
                    process_report_execution.delay(
                        execution.id, scheduled_report.owner_id
                    )
                    
                    result["reports_executed"] += 1
                    
                except Exception as e:
                    logger.exception(
                        f"Error executing scheduled report {scheduled_report.id}: {str(e)}"
                    )
                    result["errors"] += 1
    
    except Exception as e:
        logger.exception(f"Error checking scheduled reports: {str(e)}")
        result["errors"] += 1
    
    return result


@shared_task(name="business_intelligence.process_report_execution")
def process_report_execution(execution_id: int, user_id: int) -> Dict[str, Any]:
    """
    Process a report execution.
    
    This task is responsible for generating the report output and delivering it
    to the specified recipients.
    
    Args:
        execution_id: ID of the report execution to process
        user_id: ID of the user who initiated the execution
        
    Returns:
        Dictionary with execution results
    """
    logger.info(f"Processing report execution {execution_id}")
    
    result = {
        "execution_id": execution_id,
        "status": "failed",
        "outputs_generated": 0,
        "delivery_status": {}
    }
    
    try:
        with get_db_session() as db:
            # Get the execution
            execution = report_execution_service.get_report_execution(
                db, execution_id, user_id
            )
            
            if not execution:
                logger.error(f"Report execution {execution_id} not found")
                return result
            
            # Check if execution is already completed or failed
            if execution.status in [ReportExecutionStatus.COMPLETED, ReportExecutionStatus.FAILED]:
                logger.info(f"Report execution {execution_id} already {execution.status.value}")
                result["status"] = execution.status.value
                return result
            
            # Generate report outputs
            outputs = report_execution_service.generate_report_outputs(
                db, execution_id, user_id
            )
            
            result["outputs_generated"] = len(outputs)
            
            # Deliver report outputs
            if outputs:
                delivery_results = report_execution_service.deliver_report_outputs(
                    db, execution_id, user_id
                )
                
                result["delivery_status"] = delivery_results
            
            # Update execution status
            report_execution_service.update_execution_status(
                db, execution_id, ReportExecutionStatus.COMPLETED
            )
            
            result["status"] = "completed"
    
    except Exception as e:
        logger.exception(f"Error processing report execution {execution_id}: {str(e)}")
        
        try:
            with get_db_session() as db:
                # Update execution status to failed
                report_execution_service.update_execution_status(
                    db, execution_id, ReportExecutionStatus.FAILED, str(e)
                )
        except Exception as update_error:
            logger.exception(
                f"Error updating execution status for {execution_id}: {str(update_error)}"
            )
    
    return result


@shared_task(name="business_intelligence.clean_old_report_outputs")
def clean_old_report_outputs(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean old report outputs.
    
    This task is scheduled to run periodically (e.g., daily) to clean up old
    report outputs that are no longer needed.
    
    Args:
        days_to_keep: Number of days to keep report outputs
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Cleaning report outputs older than {days_to_keep} days")
    
    result = {
        "outputs_deleted": 0,
        "errors": 0
    }
    
    try:
        with get_db_session() as db:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get old outputs
            old_outputs = report_execution_service.get_old_report_outputs(
                db, cutoff_date
            )
            
            # Delete each output
            for output in old_outputs:
                try:
                    # Delete the output file
                    if output.file_path and os.path.exists(output.file_path):
                        os.remove(output.file_path)
                    
                    # Delete the output record
                    report_execution_service.delete_report_output(db, output.id)
                    
                    result["outputs_deleted"] += 1
                
                except Exception as e:
                    logger.exception(
                        f"Error deleting report output {output.id}: {str(e)}"
                    )
                    result["errors"] += 1
    
    except Exception as e:
        logger.exception(f"Error cleaning old report outputs: {str(e)}")
        result["errors"] += 1
    
    return result


@shared_task(name="business_intelligence.sync_report_data_to_elasticsearch")
def sync_report_data_to_elasticsearch() -> Dict[str, Any]:
    """
    Sync report data to Elasticsearch.
    
    This task is scheduled to run periodically (e.g., hourly) to sync report
    execution data to Elasticsearch for analytics and visualization.
    
    Returns:
        Dictionary with sync results
    """
    from backend_core.services.elasticsearch_client import ElasticsearchClient
    
    logger.info("Syncing report data to Elasticsearch")
    
    result = {
        "executions_synced": 0,
        "outputs_synced": 0,
        "errors": 0
    }
    
    try:
        es_client = ElasticsearchClient()
        
        with get_db_session() as db:
            # Get unsynced executions
            unsynced_executions = report_execution_service.get_unsynced_executions(db)
            
            # Sync each execution
            for execution in unsynced_executions:
                try:
                    # Prepare execution data for Elasticsearch
                    execution_data = {
                        "id": execution.id,
                        "template_id": execution.template_id,
                        "template_name": execution.template.name if execution.template else None,
                        "scheduled_report_id": execution.scheduled_report_id,
                        "owner_id": execution.owner_id,
                        "status": execution.status.value,
                        "parameters": execution.parameters,
                        "error_message": execution.error_message,
                        "created_at": execution.created_at.isoformat(),
                        "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
                        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                        "outputs": []
                    }
                    
                    # Add outputs data
                    for output in execution.outputs:
                        output_data = {
                            "id": output.id,
                            "format": output.format.value,
                            "file_name": output.file_name,
                            "file_size": output.file_size,
                            "created_at": output.created_at.isoformat()
                        }
                        execution_data["outputs"].append(output_data)
                        
                        # Mark output as synced
                        output.elasticsearch_synced = True
                        result["outputs_synced"] += 1
                    
                    # Index execution data
                    es_client.index(
                        index="report_executions",
                        document=execution_data,
                        document_id=str(execution.id)
                    )
                    
                    # Mark execution as synced
                    execution.elasticsearch_synced = True
                    result["executions_synced"] += 1
                
                except Exception as e:
                    logger.exception(
                        f"Error syncing report execution {execution.id}: {str(e)}"
                    )
                    result["errors"] += 1
            
            # Commit changes
            db.commit()
    
    except Exception as e:
        logger.exception(f"Error syncing report data to Elasticsearch: {str(e)}")
        result["errors"] += 1
    
    return result


@shared_task(name="business_intelligence.generate_report_usage_metrics")
def generate_report_usage_metrics() -> Dict[str, Any]:
    """
    Generate report usage metrics.
    
    This task is scheduled to run periodically (e.g., daily) to generate metrics
    about report usage for analytics and monitoring.
    
    Returns:
        Dictionary with metrics generation results
    """
    logger.info("Generating report usage metrics")
    
    result = {
        "metrics_generated": 0,
        "errors": 0
    }
    
    try:
        with get_db_session() as db:
            # Calculate metrics for the last day
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
            
            # Get executions in the time period
            executions = report_execution_service.get_executions_in_period(
                db, start_date, end_date
            )
            
            # Calculate metrics
            metrics = {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_executions": len(executions),
                "successful_executions": sum(1 for e in executions if e.status == ReportExecutionStatus.COMPLETED),
                "failed_executions": sum(1 for e in executions if e.status == ReportExecutionStatus.FAILED),
                "by_template": {},
                "by_user": {},
                "by_format": {},
                "average_execution_time_seconds": 0
            }
            
            # Calculate execution time for completed executions
            completed_executions = [e for e in executions if e.status == ReportExecutionStatus.COMPLETED and e.completed_at]
            if completed_executions:
                total_seconds = sum((e.completed_at - e.created_at).total_seconds() for e in completed_executions)
                metrics["average_execution_time_seconds"] = total_seconds / len(completed_executions)
            
            # Calculate metrics by template
            for execution in executions:
                template_id = execution.template_id
                template_name = execution.template.name if execution.template else f"Template {template_id}"
                
                if template_name not in metrics["by_template"]:
                    metrics["by_template"][template_name] = {
                        "total": 0,
                        "successful": 0,
                        "failed": 0
                    }
                
                metrics["by_template"][template_name]["total"] += 1
                
                if execution.status == ReportExecutionStatus.COMPLETED:
                    metrics["by_template"][template_name]["successful"] += 1
                elif execution.status == ReportExecutionStatus.FAILED:
                    metrics["by_template"][template_name]["failed"] += 1
            
            # Calculate metrics by user
            for execution in executions:
                user_id = execution.owner_id
                
                if user_id not in metrics["by_user"]:
                    metrics["by_user"][str(user_id)] = {
                        "total": 0,
                        "successful": 0,
                        "failed": 0
                    }
                
                metrics["by_user"][str(user_id)]["total"] += 1
                
                if execution.status == ReportExecutionStatus.COMPLETED:
                    metrics["by_user"][str(user_id)]["successful"] += 1
                elif execution.status == ReportExecutionStatus.FAILED:
                    metrics["by_user"][str(user_id)]["failed"] += 1
            
            # Calculate metrics by format
            for execution in executions:
                for output in execution.outputs:
                    format_name = output.format.value
                    
                    if format_name not in metrics["by_format"]:
                        metrics["by_format"][format_name] = 0
                    
                    metrics["by_format"][format_name] += 1
            
            # Store metrics in Redis
            metrics_key = f"report_usage_metrics:{start_date.strftime('%Y-%m-%d')}"
            redis_client.set(metrics_key, json.dumps(metrics), ex=60*60*24*30)  # Expire after 30 days
            
            result["metrics_generated"] = 1
    
    except Exception as e:
        logger.exception(f"Error generating report usage metrics: {str(e)}")
        result["errors"] += 1
    
    return result


@shared_task(name="business_intelligence.send_report_summary_notification")
def send_report_summary_notification() -> Dict[str, Any]:
    """
    Send a summary notification about report executions.
    
    This task is scheduled to run periodically (e.g., daily) to send a summary
    notification about report executions to administrators.
    
    Returns:
        Dictionary with notification results
    """
    logger.info("Sending report summary notification")
    
    result = {
        "notifications_sent": 0,
        "errors": 0
    }
    
    try:
        with get_db_session() as db:
            # Calculate metrics for the last day
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
            
            # Get executions in the time period
            executions = report_execution_service.get_executions_in_period(
                db, start_date, end_date
            )
            
            # Calculate summary
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.status == ReportExecutionStatus.COMPLETED)
            failed_executions = sum(1 for e in executions if e.status == ReportExecutionStatus.FAILED)
            
            # Get admin users
            admin_users = report_service.get_admin_users(db)
            
            # Send notification to each admin
            for admin in admin_users:
                try:
                    # Prepare notification
                    notification_data = {
                        "title": "Daily Report Execution Summary",
                        "message": f"Summary for {start_date.strftime('%Y-%m-%d')}:\n"
                                  f"Total executions: {total_executions}\n"
                                  f"Successful: {successful_executions}\n"
                                  f"Failed: {failed_executions}",
                        "type": "report_summary",
                        "link": "/business-intelligence/report-executions"
                    }
                    
                    # Send notification
                    notification_service.send_notification(
                        db, admin.id, notification_data
                    )
                    
                    result["notifications_sent"] += 1
                
                except Exception as e:
                    logger.exception(
                        f"Error sending notification to admin {admin.id}: {str(e)}"
                    )
                    result["errors"] += 1
    
    except Exception as e:
        logger.exception(f"Error sending report summary notification: {str(e)}")
        result["errors"] += 1
    
    return result
