"""
Report generators for the Business Intelligence and Reporting module.

This module provides classes for generating reports in different formats.
"""

import os
import json
import tempfile
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import uuid

# Third-party imports for report generation
import pandas as pd
import matplotlib.pyplot as plt
from jinja2 import Template
import pdfkit
import weasyprint


class BaseReportGenerator:
    """Base class for report generators."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated report file
        """
        raise NotImplementedError("Subclasses must implement generate()")


class PDFReportGenerator(BaseReportGenerator):
    """Generator for PDF reports."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a PDF report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated PDF file
        """
        # Create a temporary HTML file
        html_content = await self._render_html_template(template_data, report_data, parameters)
        
        # Create a temporary file for the PDF
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        
        # Convert HTML to PDF
        try:
            # Try using pdfkit (wkhtmltopdf)
            pdfkit.from_string(html_content, output_path)
        except Exception as e:
            # Fall back to weasyprint
            pdf = weasyprint.HTML(string=html_content).write_pdf()
            with open(output_path, 'wb') as f:
                f.write(pdf)
        
        return output_path
    
    async def _render_html_template(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render an HTML template for the report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Rendered HTML content
        """
        # Get the HTML template from template_data
        html_template = template_data.get('html_template', '')
        
        # Create a Jinja2 template
        template = Template(html_template)
        
        # Render the template with data
        context = {
            'data': report_data,
            'parameters': parameters or {},
            'generated_at': datetime.utcnow(),
            'charts': await self._generate_charts(template_data, report_data)
        }
        
        return template.render(**context)
    
    async def _generate_charts(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate charts for the report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            
        Returns:
            Dictionary mapping chart IDs to base64-encoded image data
        """
        charts = {}
        chart_definitions = template_data.get('charts', [])
        
        for chart_def in chart_definitions:
            chart_id = chart_def.get('id')
            chart_type = chart_def.get('type')
            data_source = chart_def.get('data_source')
            
            # Get data for the chart
            chart_data = self._extract_chart_data(report_data, data_source)
            
            # Generate chart
            if chart_type == 'bar':
                chart_img = self._generate_bar_chart(chart_data, chart_def)
            elif chart_type == 'line':
                chart_img = self._generate_line_chart(chart_data, chart_def)
            elif chart_type == 'pie':
                chart_img = self._generate_pie_chart(chart_data, chart_def)
            else:
                continue
            
            charts[chart_id] = chart_img
        
        return charts
    
    def _extract_chart_data(
        self, report_data: Dict[str, Any], data_source: str
    ) -> pd.DataFrame:
        """
        Extract data for a chart from the report data.
        
        Args:
            report_data: Report data
            data_source: Path to the data within report_data
            
        Returns:
            DataFrame containing the chart data
        """
        # Parse the data source path
        path_parts = data_source.split('.')
        
        # Navigate to the data
        current = report_data
        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return pd.DataFrame()
        
        # Convert to DataFrame if necessary
        if isinstance(current, list):
            return pd.DataFrame(current)
        elif isinstance(current, dict):
            return pd.DataFrame([current])
        else:
            return pd.DataFrame()
    
    def _generate_bar_chart(
        self, data: pd.DataFrame, chart_def: Dict[str, Any]
    ) -> str:
        """Generate a bar chart."""
        # Implementation omitted for brevity
        return ""
    
    def _generate_line_chart(
        self, data: pd.DataFrame, chart_def: Dict[str, Any]
    ) -> str:
        """Generate a line chart."""
        # Implementation omitted for brevity
        return ""
    
    def _generate_pie_chart(
        self, data: pd.DataFrame, chart_def: Dict[str, Any]
    ) -> str:
        """Generate a pie chart."""
        # Implementation omitted for brevity
        return ""


class CSVReportGenerator(BaseReportGenerator):
    """Generator for CSV reports."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a CSV report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated CSV file
        """
        # Create a temporary file for the CSV
        fd, output_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        
        # Get the data source from template
        data_source = template_data.get('data_source', '')
        
        # Extract the data
        data = self._extract_data(report_data, data_source)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Apply column mappings if defined
        column_mappings = template_data.get('column_mappings', {})
        if column_mappings:
            df = df.rename(columns=column_mappings)
        
        # Write to CSV
        df.to_csv(output_path, index=False)
        
        return output_path
    
    def _extract_data(
        self, report_data: Dict[str, Any], data_source: str
    ) -> List[Dict[str, Any]]:
        """
        Extract data from the report data.
        
        Args:
            report_data: Report data
            data_source: Path to the data within report_data
            
        Returns:
            List of dictionaries containing the data
        """
        # Parse the data source path
        path_parts = data_source.split('.')
        
        # Navigate to the data
        current = report_data
        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return []
        
        # Ensure the result is a list of dictionaries
        if isinstance(current, list):
            return current
        elif isinstance(current, dict):
            return [current]
        else:
            return []


class ExcelReportGenerator(BaseReportGenerator):
    """Generator for Excel reports."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an Excel report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated Excel file
        """
        # Create a temporary file for the Excel
        fd, output_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        # Create Excel writer
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        
        # Process each sheet defined in the template
        sheets = template_data.get('sheets', [])
        for sheet in sheets:
            sheet_name = sheet.get('name', 'Sheet1')
            data_source = sheet.get('data_source', '')
            
            # Extract the data
            data = self._extract_data(report_data, data_source)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Apply column mappings if defined
            column_mappings = sheet.get('column_mappings', {})
            if column_mappings:
                df = df.rename(columns=column_mappings)
            
            # Write to Excel
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Apply formatting if defined
            # (Implementation omitted for brevity)
        
        # Save the Excel file
        writer.save()
        
        return output_path
    
    def _extract_data(
        self, report_data: Dict[str, Any], data_source: str
    ) -> List[Dict[str, Any]]:
        """
        Extract data from the report data.
        
        Args:
            report_data: Report data
            data_source: Path to the data within report_data
            
        Returns:
            List of dictionaries containing the data
        """
        # Parse the data source path
        path_parts = data_source.split('.')
        
        # Navigate to the data
        current = report_data
        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return []
        
        # Ensure the result is a list of dictionaries
        if isinstance(current, list):
            return current
        elif isinstance(current, dict):
            return [current]
        else:
            return []


class HTMLReportGenerator(BaseReportGenerator):
    """Generator for HTML reports."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an HTML report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated HTML file
        """
        # Create a temporary file for the HTML
        fd, output_path = tempfile.mkstemp(suffix='.html')
        os.close(fd)
        
        # Get the HTML template from template_data
        html_template = template_data.get('html_template', '')
        
        # Create a Jinja2 template
        template = Template(html_template)
        
        # Render the template with data
        context = {
            'data': report_data,
            'parameters': parameters or {},
            'generated_at': datetime.utcnow()
        }
        
        html_content = template.render(**context)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return output_path


class JSONReportGenerator(BaseReportGenerator):
    """Generator for JSON reports."""
    
    async def generate(
        self, 
        template_data: Dict[str, Any], 
        report_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a JSON report.
        
        Args:
            template_data: Template data defining the report structure
            report_data: Data to include in the report
            parameters: Parameters used to generate the report
            
        Returns:
            Path to the generated JSON file
        """
        # Create a temporary file for the JSON
        fd, output_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        
        # Get the data source from template
        data_source = template_data.get('data_source', '')
        
        # Extract the data
        data = self._extract_data(report_data, data_source)
        
        # Add metadata
        result = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'parameters': parameters or {}
            },
            'data': data
        }
        
        # Write to JSON
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return output_path
    
    def _extract_data(
        self, report_data: Dict[str, Any], data_source: str
    ) -> Any:
        """
        Extract data from the report data.
        
        Args:
            report_data: Report data
            data_source: Path to the data within report_data
            
        Returns:
            Extracted data
        """
        if not data_source:
            return report_data
        
        # Parse the data source path
        path_parts = data_source.split('.')
        
        # Navigate to the data
        current = report_data
        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return None
        
        return current
