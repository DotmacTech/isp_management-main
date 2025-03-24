"""
Test module for the Reporting Service in the Field Services Module.
"""

import pytest
import calendar
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import func
from sqlalchemy.orm import Session
from modules.field_services.models import (
    Job, JobStatusEnum, JobPriorityEnum, JobTypeEnum,
    Technician, TechnicianStatusEnum, JobHistory,
    TechnicianInventory, InventoryTransaction, InventoryTransactionTypeEnum
)
from modules.field_services.services import ReportingService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def reporting_service(mock_db):
    """Create a ReportingService instance with a mock database."""
    return ReportingService(mock_db)


@pytest.fixture
def sample_jobs():
    """Create sample jobs for testing."""
    now = datetime.utcnow()
    
    jobs = [
        # Completed job with SLA met
        Job(
            id=1,
            title="Router Installation",
            description="Install new router",
            customer_id=1,
            job_type=JobTypeEnum.INSTALLATION,
            status=JobStatusEnum.COMPLETED,
            priority=JobPriorityEnum.MEDIUM,
            technician_id=1,
            estimated_duration_minutes=60,
            scheduled_start_time=now - timedelta(days=1, hours=2),
            scheduled_end_time=now - timedelta(days=1, hours=1),
            actual_start_time=now - timedelta(days=1, hours=2),
            actual_end_time=now - timedelta(days=1, hours=1, minutes=15),
            sla_deadline=now - timedelta(days=1),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1)
        ),
        # Completed job with SLA breached
        Job(
            id=2,
            title="Network Troubleshooting",
            description="Fix network connectivity issues",
            customer_id=2,
            job_type=JobTypeEnum.REPAIR,
            status=JobStatusEnum.COMPLETED,
            priority=JobPriorityEnum.HIGH,
            technician_id=2,
            estimated_duration_minutes=90,
            scheduled_start_time=now - timedelta(days=1, hours=5),
            scheduled_end_time=now - timedelta(days=1, hours=3, minutes=30),
            actual_start_time=now - timedelta(days=1, hours=5),
            actual_end_time=now - timedelta(days=1, hours=2),
            sla_deadline=now - timedelta(days=1, hours=3),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1)
        ),
        # In-progress job
        Job(
            id=3,
            title="Fiber Connection Setup",
            description="Setup fiber connection",
            customer_id=3,
            job_type=JobTypeEnum.INSTALLATION,
            status=JobStatusEnum.IN_PROGRESS,
            priority=JobPriorityEnum.MEDIUM,
            technician_id=1,
            estimated_duration_minutes=120,
            scheduled_start_time=now - timedelta(hours=2),
            scheduled_end_time=now + timedelta(hours=2),
            actual_start_time=now - timedelta(hours=1),
            actual_end_time=None,
            sla_deadline=now + timedelta(hours=3),
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=1)
        ),
        # Pending job
        Job(
            id=4,
            title="Equipment Maintenance",
            description="Regular maintenance",
            customer_id=4,
            job_type=JobTypeEnum.MAINTENANCE,
            status=JobStatusEnum.PENDING,
            priority=JobPriorityEnum.LOW,
            technician_id=None,
            estimated_duration_minutes=45,
            scheduled_start_time=now + timedelta(days=1),
            scheduled_end_time=now + timedelta(days=1, hours=1),
            actual_start_time=None,
            actual_end_time=None,
            sla_deadline=now + timedelta(days=2),
            created_at=now - timedelta(hours=5),
            updated_at=now - timedelta(hours=5)
        )
    ]
    
    return jobs


@pytest.fixture
def sample_technicians():
    """Create sample technicians for testing."""
    technicians = [
        Technician(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890",
            status=TechnicianStatusEnum.AVAILABLE,
            skills=["networking", "installation", "troubleshooting"],
            created_at=datetime.utcnow() - timedelta(days=30)
        ),
        Technician(
            id=2,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="987-654-3210",
            status=TechnicianStatusEnum.ON_JOB,
            skills=["fiber", "repair", "networking"],
            created_at=datetime.utcnow() - timedelta(days=20)
        )
    ]
    
    return technicians


class TestReportingService:
    """Test cases for the ReportingService class."""

    def test_get_job_performance_report(self, reporting_service, mock_db, sample_jobs):
        """Test generating job performance report."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=3)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        # Mock job query
        mock_db.query.return_value.filter.return_value.all.return_value = sample_jobs
        
        # Act
        report = reporting_service.get_job_performance_report(start_date, end_date)
        
        # Assert
        assert report["period"]["start_date"] == start_date
        assert report["period"]["end_date"] == end_date
        assert report["summary"]["total_jobs"] == 4
        assert report["summary"]["completed_jobs"] == 2
        assert report["summary"]["cancelled_jobs"] == 0
        
        # Check completion rate (2/4 = 50%)
        assert report["summary"]["completion_rate"] == 50.0
        
        # Check SLA compliance rate (1/2 = 50% for completed jobs with SLA)
        assert report["summary"]["sla_compliance_rate"] == 50.0
        
        # Check distributions
        assert len(report["distributions"]["by_type"]) == 3  # INSTALLATION, REPAIR, MAINTENANCE
        assert len(report["distributions"]["by_priority"]) == 3  # HIGH, MEDIUM, LOW
        assert len(report["distributions"]["by_status"]) == 3  # COMPLETED, IN_PROGRESS, PENDING
        
        # Check HATEOAS links
        assert "links" in report
        assert any(link["rel"] == "self" for link in report["links"])

    def test_get_technician_efficiency_report(self, reporting_service, mock_db, sample_technicians, sample_jobs):
        """Test generating technician efficiency report."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=3)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        # Mock technician query
        mock_db.query.return_value.all.return_value = sample_technicians
        
        # Mock job queries for each technician
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [job for job in sample_jobs if job.technician_id == 1],  # Jobs for technician 1
            [job for job in sample_jobs if job.technician_id == 2]   # Jobs for technician 2
        ]
        
        # Mock working days calculation
        with patch.object(reporting_service, '_calculate_working_days') as mock_calc_days:
            mock_calc_days.return_value = 4  # 4 working days in the period
            
            # Act
            report = reporting_service.get_technician_efficiency_report(start_date, end_date)
        
        # Assert
        assert report["period"]["start_date"] == start_date
        assert report["period"]["end_date"] == end_date
        assert report["period"]["working_days"] == 4
        
        # Check technician metrics
        assert len(report["technicians"]) == 2
        
        # Technician 1 has 1 completed job
        tech1 = next(t for t in report["technicians"] if t["technician_id"] == 1)
        assert tech1["total_jobs"] == 2  # 1 completed, 1 in-progress
        assert tech1["completed_jobs"] == 1
        assert tech1["jobs_per_day"] == 0.25  # 1 job / 4 days
        
        # Technician 2 has 1 completed job
        tech2 = next(t for t in report["technicians"] if t["technician_id"] == 2)
        assert tech2["total_jobs"] == 1  # 1 completed
        assert tech2["completed_jobs"] == 1
        assert tech2["jobs_per_day"] == 0.25  # 1 job / 4 days
        
        # Check HATEOAS links
        assert "links" in report
        assert any(link["rel"] == "self" for link in report["links"])
        assert any(link["rel"] == "technician" for link in tech1["links"])
        assert any(link["rel"] == "technician" for link in tech2["links"])

    def test_get_sla_compliance_report(self, reporting_service, mock_db, sample_jobs):
        """Test generating SLA compliance report."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=3)
        end_date = datetime.utcnow() + timedelta(days=3)
        
        # Mock job query
        mock_db.query.return_value.filter.return_value.all.return_value = sample_jobs
        
        # Act
        report = reporting_service.get_sla_compliance_report(start_date, end_date)
        
        # Assert
        assert report["period"]["start_date"] == start_date
        assert report["period"]["end_date"] == end_date
        
        # Check summary
        assert report["summary"]["total_jobs_with_sla"] == 4  # All jobs have SLA
        assert report["summary"]["completed_jobs"] == 2  # 2 completed jobs
        assert report["summary"]["sla_met"] == 1  # 1 job met SLA
        assert report["summary"]["sla_breached"] == 1  # 1 job breached SLA
        assert report["summary"]["overall_compliance_rate"] == 50.0  # 1/2 = 50%
        
        # Check compliance by type
        assert "compliance_by_type" in report
        assert "compliance_by_priority" in report
        
        # Check HATEOAS links
        assert "links" in report
        assert any(link["rel"] == "self" for link in report["links"])

    def test_get_dashboard_metrics(self, reporting_service, mock_db):
        """Test getting dashboard metrics."""
        # Arrange
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59)
        
        # Mock active technicians count
        mock_db.query.return_value.filter.return_value.count.side_effect = [
            3,  # active technicians
            2,  # jobs at risk
        ]
        
        # Mock period metrics
        with patch.object(reporting_service, '_get_period_metrics') as mock_get_metrics:
            mock_get_metrics.side_effect = [
                {  # Today's metrics
                    "jobs_created": 5,
                    "jobs_completed": 3,
                    "sla_compliance_rate": 66.67,
                    "avg_resolution_time_minutes": 45.5
                },
                {  # This week's metrics
                    "jobs_created": 15,
                    "jobs_completed": 10,
                    "sla_compliance_rate": 80.0,
                    "avg_resolution_time_minutes": 52.3
                },
                {  # This month's metrics
                    "jobs_created": 45,
                    "jobs_completed": 38,
                    "sla_compliance_rate": 78.9,
                    "avg_resolution_time_minutes": 55.7
                }
            ]
            
            # Act
            dashboard = reporting_service.get_dashboard_metrics()
            
            # Assert
            assert dashboard["active_technicians"] == 3
            assert dashboard["jobs_at_risk"] == 2
            
            # Check today's metrics
            assert dashboard["today"]["metrics"]["jobs_created"] == 5
            assert dashboard["today"]["metrics"]["jobs_completed"] == 3
            assert dashboard["today"]["metrics"]["sla_compliance_rate"] == 66.67
            
            # Check this week's metrics
            assert dashboard["this_week"]["metrics"]["jobs_created"] == 15
            assert dashboard["this_week"]["metrics"]["jobs_completed"] == 10
            
            # Check this month's metrics
            assert dashboard["this_month"]["metrics"]["jobs_created"] == 45
            assert dashboard["this_month"]["metrics"]["jobs_completed"] == 38
            
            # Check HATEOAS links
            assert "links" in dashboard
            assert any(link["rel"] == "self" for link in dashboard["links"])

    def test_get_period_metrics(self, reporting_service, mock_db):
        """Test getting metrics for a specific time period."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Mock jobs created count
        mock_db.query.return_value.filter.return_value.count.side_effect = [
            10,  # jobs created
            8    # jobs completed
        ]
        
        # Mock completed jobs with SLA
        mock_completed_jobs_with_sla = []
        # 5 jobs that met SLA
        for i in range(1, 6):
            job = MagicMock()
            job.actual_end_time = datetime.utcnow() - timedelta(hours=i)
            job.sla_deadline = datetime.utcnow()
            mock_completed_jobs_with_sla.append(job)
        
        # 2 jobs that breached SLA
        for i in range(1, 3):
            job = MagicMock()
            job.actual_end_time = datetime.utcnow()
            job.sla_deadline = datetime.utcnow() - timedelta(hours=i)
            mock_completed_jobs_with_sla.append(job)
        
        # Mock completed jobs for resolution time
        mock_completed_jobs = []
        job1 = MagicMock()
        job1.actual_start_time = datetime.utcnow() - timedelta(hours=2)
        job1.actual_end_time = datetime.utcnow() - timedelta(hours=1)
        mock_completed_jobs.append(job1)
        
        job2 = MagicMock()
        job2.actual_start_time = datetime.utcnow() - timedelta(minutes=90)
        job2.actual_end_time = datetime.utcnow() - timedelta(minutes=30)
        mock_completed_jobs.append(job2)
        
        # Set up mock query returns
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            mock_completed_jobs_with_sla,  # First call for SLA compliance
            mock_completed_jobs            # Second call for resolution time
        ]
        
        # Act
        metrics = reporting_service._get_period_metrics(start_date, end_date)
        
        # Assert
        assert metrics["jobs_created"] == 10
        assert metrics["jobs_completed"] == 8
        assert metrics["sla_compliance_rate"] == 71.43  # 5/7 ≈ 71.43%
        assert metrics["avg_resolution_time_minutes"] == 60.0  # (60 + 60) / 2 = 60 minutes

    def test_calculate_working_days(self, reporting_service):
        """Test calculating the number of working days between two dates."""
        # Arrange
        # Monday to Friday (5 working days)
        start_date = datetime(2023, 1, 2, 0, 0, 0)  # Monday
        end_date = datetime(2023, 1, 6, 23, 59, 59)  # Friday
        
        # Act
        result1 = reporting_service._calculate_working_days(start_date, end_date)
        
        # Monday to Monday (6 working days)
        start_date2 = datetime(2023, 1, 2, 0, 0, 0)  # Monday
        end_date2 = datetime(2023, 1, 9, 23, 59, 59)  # Monday next week
        
        # Act
        result2 = reporting_service._calculate_working_days(start_date2, end_date2)
        
        # Assert
        assert result1 == 5  # Monday to Friday
        assert result2 == 6  # Monday to Monday (includes 6 working days)
