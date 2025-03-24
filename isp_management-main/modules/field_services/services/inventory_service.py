"""
Inventory Service for the Field Services Module.

This service handles inventory management for field technicians, including equipment tracking,
inventory allocation, and stock management.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_, or_, desc, case
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Inventory, InventoryStatusEnum, InventoryType, 
    TechnicianInventory, InventoryTransaction, InventoryTransactionTypeEnum,
    Job, JobStatusEnum
)
from ..schemas import (
    InventoryCreate, InventoryUpdate, InventoryResponse,
    TechnicianInventoryCreate, TechnicianInventoryUpdate, TechnicianInventoryResponse,
    InventoryTransactionCreate, InventoryTransactionResponse
)
from backend_core.utils.hateoas import add_resource_links


class InventoryService:
    """Service for managing field service inventory."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_inventory_item(self, inventory_data: InventoryCreate, user_id: int) -> InventoryResponse:
        """Create a new inventory item."""
        # Create inventory object from schema
        inventory = Inventory(
            name=inventory_data.name,
            description=inventory_data.description,
            sku=inventory_data.sku,
            inventory_type=inventory_data.inventory_type,
            status=InventoryStatusEnum[inventory_data.status.upper()],
            quantity=inventory_data.quantity,
            min_quantity=inventory_data.min_quantity,
            max_quantity=inventory_data.max_quantity,
            unit_cost=inventory_data.unit_cost,
            location=inventory_data.location,
            created_by=user_id
        )
        
        # Add to database
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)
        
        # Create initial inventory transaction
        if inventory.quantity > 0:
            transaction = InventoryTransaction(
                inventory_id=inventory.id,
                transaction_type=InventoryTransactionTypeEnum.INITIAL,
                quantity=inventory.quantity,
                notes="Initial inventory creation",
                created_by=user_id
            )
            self.db.add(transaction)
            self.db.commit()
        
        # Convert to response model
        return self._to_inventory_response(inventory)
    
    def get_inventory_items(
        self, 
        status: Optional[str] = None,
        inventory_type: Optional[str] = None,
        low_stock: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryResponse], int]:
        """Get inventory items with optional filtering."""
        query = self.db.query(Inventory)
        
        # Apply filters
        if status:
            query = query.filter(Inventory.status == InventoryStatusEnum[status.upper()])
        
        if inventory_type:
            query = query.filter(Inventory.inventory_type == inventory_type)
        
        if low_stock:
            query = query.filter(Inventory.quantity <= Inventory.min_quantity)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Inventory.name.ilike(search_term),
                    Inventory.description.ilike(search_term),
                    Inventory.sku.ilike(search_term)
                )
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(Inventory.name)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        inventory_items = query.all()
        
        # Convert to response models
        inventory_responses = [self._to_inventory_response(item) for item in inventory_items]
        
        return inventory_responses, total
    
    def get_inventory_by_id(self, inventory_id: int) -> Optional[InventoryResponse]:
        """Get an inventory item by ID."""
        inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
        
        if not inventory:
            return None
        
        return self._to_inventory_response(inventory)
    
    def update_inventory(self, inventory_id: int, inventory_data: InventoryUpdate, user_id: int) -> Optional[InventoryResponse]:
        """Update an inventory item."""
        inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
        
        if not inventory:
            return None
        
        # Store previous quantity for transaction tracking
        previous_quantity = inventory.quantity
        
        # Update fields if provided
        if inventory_data.name is not None:
            inventory.name = inventory_data.name
        
        if inventory_data.description is not None:
            inventory.description = inventory_data.description
        
        if inventory_data.sku is not None:
            inventory.sku = inventory_data.sku
        
        if inventory_data.inventory_type is not None:
            inventory.inventory_type = inventory_data.inventory_type
        
        if inventory_data.status is not None:
            inventory.status = InventoryStatusEnum[inventory_data.status.upper()]
        
        if inventory_data.quantity is not None:
            inventory.quantity = inventory_data.quantity
        
        if inventory_data.min_quantity is not None:
            inventory.min_quantity = inventory_data.min_quantity
        
        if inventory_data.max_quantity is not None:
            inventory.max_quantity = inventory_data.max_quantity
        
        if inventory_data.unit_cost is not None:
            inventory.unit_cost = inventory_data.unit_cost
        
        if inventory_data.location is not None:
            inventory.location = inventory_data.location
        
        # Update the updated_by field
        inventory.updated_by = user_id
        
        # Commit changes
        self.db.commit()
        self.db.refresh(inventory)
        
        # Create inventory transaction if quantity changed
        if inventory.quantity != previous_quantity:
            quantity_change = inventory.quantity - previous_quantity
            transaction_type = InventoryTransactionTypeEnum.ADJUSTMENT
            
            transaction = InventoryTransaction(
                inventory_id=inventory.id,
                transaction_type=transaction_type,
                quantity=quantity_change,
                notes=f"Manual inventory adjustment from {previous_quantity} to {inventory.quantity}",
                created_by=user_id
            )
            self.db.add(transaction)
            self.db.commit()
        
        # Convert to response model
        return self._to_inventory_response(inventory)
    
    def delete_inventory(self, inventory_id: int) -> bool:
        """Delete an inventory item."""
        inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
        
        if not inventory:
            return False
        
        # Check if inventory is in use by technicians
        tech_inventory = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.inventory_id == inventory_id
        ).first()
        
        if tech_inventory:
            return False
        
        # Delete inventory
        self.db.delete(inventory)
        self.db.commit()
        
        return True
    
    def assign_inventory_to_technician(
        self, 
        technician_inventory_data: TechnicianInventoryCreate, 
        user_id: int
    ) -> TechnicianInventoryResponse:
        """Assign inventory to a technician."""
        # Check if inventory exists and has enough quantity
        inventory = self.db.query(Inventory).filter(Inventory.id == technician_inventory_data.inventory_id).first()
        
        if not inventory or inventory.quantity < technician_inventory_data.quantity:
            raise ValueError("Insufficient inventory quantity available")
        
        # Check if technician already has this inventory item
        existing = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.technician_id == technician_inventory_data.technician_id,
            TechnicianInventory.inventory_id == technician_inventory_data.inventory_id
        ).first()
        
        if existing:
            # Update existing record
            previous_quantity = existing.quantity
            existing.quantity += technician_inventory_data.quantity
            existing.updated_by = user_id
            
            # Update main inventory
            inventory.quantity -= technician_inventory_data.quantity
            
            # Commit changes
            self.db.commit()
            self.db.refresh(existing)
            
            # Create inventory transaction
            transaction = InventoryTransaction(
                inventory_id=inventory.id,
                transaction_type=InventoryTransactionTypeEnum.TECHNICIAN_ASSIGNMENT,
                quantity=-technician_inventory_data.quantity,
                notes=f"Additional inventory assigned to technician ID {technician_inventory_data.technician_id}",
                technician_id=technician_inventory_data.technician_id,
                created_by=user_id
            )
            self.db.add(transaction)
            self.db.commit()
            
            return self._to_technician_inventory_response(existing)
        else:
            # Create new technician inventory record
            technician_inventory = TechnicianInventory(
                technician_id=technician_inventory_data.technician_id,
                inventory_id=technician_inventory_data.inventory_id,
                quantity=technician_inventory_data.quantity,
                created_by=user_id
            )
            
            # Update main inventory
            inventory.quantity -= technician_inventory_data.quantity
            
            # Add to database
            self.db.add(technician_inventory)
            self.db.commit()
            self.db.refresh(technician_inventory)
            
            # Create inventory transaction
            transaction = InventoryTransaction(
                inventory_id=inventory.id,
                transaction_type=InventoryTransactionTypeEnum.TECHNICIAN_ASSIGNMENT,
                quantity=-technician_inventory_data.quantity,
                notes=f"Inventory assigned to technician ID {technician_inventory_data.technician_id}",
                technician_id=technician_inventory_data.technician_id,
                created_by=user_id
            )
            self.db.add(transaction)
            self.db.commit()
            
            return self._to_technician_inventory_response(technician_inventory)
    
    def get_technician_inventory(
        self, 
        technician_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TechnicianInventoryResponse], int]:
        """Get inventory assigned to a technician."""
        query = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.technician_id == technician_id
        ).options(
            joinedload(TechnicianInventory.inventory)
        )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(TechnicianInventory.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        technician_inventory = query.all()
        
        # Convert to response models
        inventory_responses = [self._to_technician_inventory_response(item) for item in technician_inventory]
        
        return inventory_responses, total
    
    def update_technician_inventory(
        self, 
        technician_id: int, 
        inventory_id: int, 
        inventory_data: TechnicianInventoryUpdate, 
        user_id: int
    ) -> Optional[TechnicianInventoryResponse]:
        """Update inventory assigned to a technician."""
        technician_inventory = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.technician_id == technician_id,
            TechnicianInventory.inventory_id == inventory_id
        ).first()
        
        if not technician_inventory:
            return None
        
        # Store previous quantity for transaction tracking
        previous_quantity = technician_inventory.quantity
        
        # Calculate quantity change
        quantity_change = inventory_data.quantity - previous_quantity
        
        # If increasing quantity, check if main inventory has enough
        if quantity_change > 0:
            inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
            if not inventory or inventory.quantity < quantity_change:
                raise ValueError("Insufficient inventory quantity available")
            
            # Update main inventory
            inventory.quantity -= quantity_change
        else:
            # Return inventory to main stock
            inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
            if inventory:
                inventory.quantity += abs(quantity_change)
        
        # Update technician inventory
        technician_inventory.quantity = inventory_data.quantity
        technician_inventory.updated_by = user_id
        
        # If quantity is zero, delete the record
        if technician_inventory.quantity <= 0:
            self.db.delete(technician_inventory)
            self.db.commit()
            
            # Create inventory transaction
            transaction = InventoryTransaction(
                inventory_id=inventory_id,
                transaction_type=InventoryTransactionTypeEnum.TECHNICIAN_RETURN,
                quantity=abs(previous_quantity),
                notes=f"All inventory returned from technician ID {technician_id}",
                technician_id=technician_id,
                created_by=user_id
            )
            self.db.add(transaction)
            self.db.commit()
            
            return None
        
        # Commit changes
        self.db.commit()
        self.db.refresh(technician_inventory)
        
        # Create inventory transaction
        transaction_type = InventoryTransactionTypeEnum.TECHNICIAN_ASSIGNMENT if quantity_change > 0 else InventoryTransactionTypeEnum.TECHNICIAN_RETURN
        transaction = InventoryTransaction(
            inventory_id=inventory_id,
            transaction_type=transaction_type,
            quantity=-quantity_change if quantity_change > 0 else abs(quantity_change),
            notes=f"Technician inventory updated from {previous_quantity} to {technician_inventory.quantity}",
            technician_id=technician_id,
            created_by=user_id
        )
        self.db.add(transaction)
        self.db.commit()
        
        return self._to_technician_inventory_response(technician_inventory)
    
    def record_inventory_usage(
        self, 
        technician_id: int, 
        inventory_id: int, 
        quantity: int, 
        job_id: Optional[int] = None, 
        notes: Optional[str] = None,
        user_id: int = None
    ) -> bool:
        """Record inventory usage by a technician for a job."""
        # Check if technician has enough inventory
        technician_inventory = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.technician_id == technician_id,
            TechnicianInventory.inventory_id == inventory_id
        ).first()
        
        if not technician_inventory or technician_inventory.quantity < quantity:
            return False
        
        # Update technician inventory
        technician_inventory.quantity -= quantity
        
        # If quantity is zero, delete the record
        if technician_inventory.quantity <= 0:
            self.db.delete(technician_inventory)
        
        # Commit changes
        self.db.commit()
        
        # Create inventory transaction
        transaction = InventoryTransaction(
            inventory_id=inventory_id,
            transaction_type=InventoryTransactionTypeEnum.USAGE,
            quantity=-quantity,
            notes=notes or f"Inventory used by technician ID {technician_id}" + (f" for job ID {job_id}" if job_id else ""),
            technician_id=technician_id,
            job_id=job_id,
            created_by=user_id or technician_id
        )
        self.db.add(transaction)
        self.db.commit()
        
        return True
    
    def get_inventory_transactions(
        self, 
        inventory_id: Optional[int] = None,
        technician_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryTransactionResponse], int]:
        """Get inventory transactions with optional filtering."""
        query = self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.inventory),
            joinedload(InventoryTransaction.technician),
            joinedload(InventoryTransaction.job)
        )
        
        # Apply filters
        if inventory_id:
            query = query.filter(InventoryTransaction.inventory_id == inventory_id)
        
        if technician_id:
            query = query.filter(InventoryTransaction.technician_id == technician_id)
        
        if transaction_type:
            query = query.filter(InventoryTransaction.transaction_type == InventoryTransactionTypeEnum[transaction_type.upper()])
        
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
            query = query.filter(InventoryTransaction.created_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
            query = query.filter(InventoryTransaction.created_at <= end_datetime)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(InventoryTransaction.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        transactions = query.all()
        
        # Convert to response models
        transaction_responses = [self._to_transaction_response(transaction) for transaction in transactions]
        
        return transaction_responses, total
    
    def create_inventory_transaction(
        self, 
        transaction_data: InventoryTransactionCreate, 
        user_id: int
    ) -> InventoryTransactionResponse:
        """Create a new inventory transaction."""
        # Get inventory item
        inventory = self.db.query(Inventory).filter(Inventory.id == transaction_data.inventory_id).first()
        
        if not inventory:
            raise ValueError("Inventory item not found")
        
        # Create transaction object
        transaction = InventoryTransaction(
            inventory_id=transaction_data.inventory_id,
            transaction_type=InventoryTransactionTypeEnum[transaction_data.transaction_type.upper()],
            quantity=transaction_data.quantity,
            notes=transaction_data.notes,
            technician_id=transaction_data.technician_id,
            job_id=transaction_data.job_id,
            created_by=user_id
        )
        
        # Update inventory quantity
        inventory.quantity += transaction_data.quantity
        
        # Add to database
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Convert to response model
        return self._to_transaction_response(transaction)
    
    def get_inventory_metrics(self) -> Dict[str, Any]:
        """Get inventory metrics and statistics."""
        # Get total inventory count
        total_inventory = self.db.query(Inventory).count()
        
        # Get low stock items count
        low_stock = self.db.query(Inventory).filter(
            Inventory.quantity <= Inventory.min_quantity
        ).count()
        
        # Get out of stock items count
        out_of_stock = self.db.query(Inventory).filter(
            Inventory.quantity == 0
        ).count()
        
        # Get inventory value
        inventory_value = self.db.query(
            func.sum(Inventory.quantity * Inventory.unit_cost)
        ).scalar() or 0
        
        # Get inventory by type
        inventory_by_type = self.db.query(
            Inventory.inventory_type,
            func.count(Inventory.id).label('count'),
            func.sum(Inventory.quantity).label('total_quantity'),
            func.sum(Inventory.quantity * Inventory.unit_cost).label('total_value')
        ).group_by(Inventory.inventory_type).all()
        
        inventory_type_stats = {
            item.inventory_type: {
                'count': item.count,
                'total_quantity': item.total_quantity,
                'total_value': item.total_value
            }
            for item in inventory_by_type
        }
        
        # Get inventory by status
        inventory_by_status = self.db.query(
            Inventory.status,
            func.count(Inventory.id).label('count')
        ).group_by(Inventory.status).all()
        
        inventory_status_stats = {
            item.status.value: item.count
            for item in inventory_by_status
        }
        
        # Get technician inventory stats
        technician_inventory = self.db.query(
            TechnicianInventory.technician_id,
            func.count(TechnicianInventory.inventory_id).label('item_count'),
            func.sum(TechnicianInventory.quantity).label('total_quantity')
        ).group_by(TechnicianInventory.technician_id).all()
        
        technician_stats = {
            item.technician_id: {
                'item_count': item.item_count,
                'total_quantity': item.total_quantity
            }
            for item in technician_inventory
        }
        
        # Get recent transactions
        recent_transactions = self.db.query(InventoryTransaction).order_by(
            InventoryTransaction.created_at.desc()
        ).limit(10).all()
        
        recent_transaction_data = [
            {
                'id': transaction.id,
                'inventory_id': transaction.inventory_id,
                'inventory_name': transaction.inventory.name if transaction.inventory else None,
                'transaction_type': transaction.transaction_type.value,
                'quantity': transaction.quantity,
                'technician_id': transaction.technician_id,
                'job_id': transaction.job_id,
                'created_at': transaction.created_at
            }
            for transaction in recent_transactions
        ]
        
        # Return metrics
        return {
            "total_inventory_items": total_inventory,
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
            "total_inventory_value": inventory_value,
            "inventory_by_type": inventory_type_stats,
            "inventory_by_status": inventory_status_stats,
            "technician_inventory": technician_stats,
            "recent_transactions": recent_transaction_data
        }
    
    def get_inventory_usage_by_job_type(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get inventory usage statistics by job type."""
        # Parse dates
        start_datetime = datetime.fromisoformat(start_date) if start_date else datetime.utcnow().replace(month=1, day=1)
        end_datetime = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        
        # Get inventory usage transactions with job information
        transactions = self.db.query(
            InventoryTransaction,
            Job.job_type
        ).join(
            Job,
            InventoryTransaction.job_id == Job.id
        ).filter(
            InventoryTransaction.transaction_type == InventoryTransactionTypeEnum.USAGE,
            InventoryTransaction.created_at.between(start_datetime, end_datetime),
            InventoryTransaction.job_id != None
        ).all()
        
        # Group usage by job type
        usage_by_job_type = {}
        for transaction, job_type in transactions:
            job_type_value = job_type.value
            
            if job_type_value not in usage_by_job_type:
                usage_by_job_type[job_type_value] = {
                    'total_quantity': 0,
                    'items': {}
                }
            
            usage_by_job_type[job_type_value]['total_quantity'] += abs(transaction.quantity)
            
            # Track usage by inventory item
            inventory_id = transaction.inventory_id
            inventory_name = transaction.inventory.name if transaction.inventory else f"Item {inventory_id}"
            
            if inventory_id not in usage_by_job_type[job_type_value]['items']:
                usage_by_job_type[job_type_value]['items'][inventory_id] = {
                    'name': inventory_name,
                    'quantity': 0
                }
            
            usage_by_job_type[job_type_value]['items'][inventory_id]['quantity'] += abs(transaction.quantity)
        
        # Convert items dict to list for each job type
        for job_type in usage_by_job_type:
            usage_by_job_type[job_type]['items'] = list(usage_by_job_type[job_type]['items'].values())
            usage_by_job_type[job_type]['items'].sort(key=lambda x: x['quantity'], reverse=True)
        
        # Return usage statistics
        return {
            "period_start": start_datetime,
            "period_end": end_datetime,
            "usage_by_job_type": usage_by_job_type
        }
    
    def _to_inventory_response(self, inventory: Inventory) -> InventoryResponse:
        """Convert Inventory model to InventoryResponse schema."""
        # Calculate stock status
        stock_status = "normal"
        if inventory.quantity <= 0:
            stock_status = "out_of_stock"
        elif inventory.quantity <= inventory.min_quantity:
            stock_status = "low_stock"
        elif inventory.quantity >= inventory.max_quantity:
            stock_status = "overstocked"
        
        response_dict = {
            "id": inventory.id,
            "name": inventory.name,
            "description": inventory.description,
            "sku": inventory.sku,
            "inventory_type": inventory.inventory_type,
            "status": inventory.status.value,
            "quantity": inventory.quantity,
            "min_quantity": inventory.min_quantity,
            "max_quantity": inventory.max_quantity,
            "unit_cost": inventory.unit_cost,
            "location": inventory.location,
            "stock_status": stock_status,
            "created_by": inventory.created_by,
            "updated_by": inventory.updated_by,
            "created_at": inventory.created_at,
            "updated_at": inventory.updated_at
        }
        
        # Add HATEOAS links
        add_resource_links(response_dict, "field-services.inventory", inventory.id)
        
        return InventoryResponse(**response_dict)
    
    def _to_technician_inventory_response(self, technician_inventory: TechnicianInventory) -> TechnicianInventoryResponse:
        """Convert TechnicianInventory model to TechnicianInventoryResponse schema."""
        inventory_name = technician_inventory.inventory.name if technician_inventory.inventory else None
        inventory_type = technician_inventory.inventory.inventory_type if technician_inventory.inventory else None
        
        response_dict = {
            "technician_id": technician_inventory.technician_id,
            "inventory_id": technician_inventory.inventory_id,
            "inventory_name": inventory_name,
            "inventory_type": inventory_type,
            "quantity": technician_inventory.quantity,
            "created_by": technician_inventory.created_by,
            "updated_by": technician_inventory.updated_by,
            "created_at": technician_inventory.created_at,
            "updated_at": technician_inventory.updated_at
        }
        
        # Add HATEOAS links
        links = [
            {"rel": "self", "href": f"/api/field-services/technicians/{technician_inventory.technician_id}/inventory/{technician_inventory.inventory_id}"},
            {"rel": "technician", "href": f"/api/field-services/technicians/{technician_inventory.technician_id}"},
            {"rel": "inventory", "href": f"/api/field-services/inventory/{technician_inventory.inventory_id}"}
        ]
        response_dict["links"] = links
        
        return TechnicianInventoryResponse(**response_dict)
    
    def _to_transaction_response(self, transaction: InventoryTransaction) -> InventoryTransactionResponse:
        """Convert InventoryTransaction model to InventoryTransactionResponse schema."""
        inventory_name = transaction.inventory.name if transaction.inventory else None
        technician_name = transaction.technician.name if transaction.technician else None
        job_title = transaction.job.title if transaction.job else None
        
        response_dict = {
            "id": transaction.id,
            "inventory_id": transaction.inventory_id,
            "inventory_name": inventory_name,
            "transaction_type": transaction.transaction_type.value,
            "quantity": transaction.quantity,
            "notes": transaction.notes,
            "technician_id": transaction.technician_id,
            "technician_name": technician_name,
            "job_id": transaction.job_id,
            "job_title": job_title,
            "created_by": transaction.created_by,
            "created_at": transaction.created_at
        }
        
        # Add HATEOAS links
        links = [
            {"rel": "self", "href": f"/api/field-services/inventory/transactions/{transaction.id}"},
            {"rel": "inventory", "href": f"/api/field-services/inventory/{transaction.inventory_id}"}
        ]
        
        if transaction.technician_id:
            links.append({"rel": "technician", "href": f"/api/field-services/technicians/{transaction.technician_id}"})
        
        if transaction.job_id:
            links.append({"rel": "job", "href": f"/api/field-services/jobs/{transaction.job_id}"})
        
        response_dict["links"] = links
        
        return InventoryTransactionResponse(**response_dict)
