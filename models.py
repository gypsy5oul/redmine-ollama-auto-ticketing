#!/usr/bin/env python3
"""
Pydantic Models for DevOps Automation API
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TicketAssignment(BaseModel):
    user_id: int
    name: str
    max_tickets: Optional[int] = None

class ProcessedTicket(BaseModel):
    ticket_id: int
    subject: str
    original_priority: str
    adjusted_priority: str
    environment: str
    priority_downgraded: bool
    assigned_to: TicketAssignment
    assignment_type: str
    reason: str
    ai_analysis: str
    ai_analysis_short: str
    redmine_url: str
    success: bool
    error: Optional[str] = None

class AutomationResponse(BaseModel):
    success: bool
    processed_tickets: List[ProcessedTicket]
    total_processed: int
    priority_adjustments: int
    ollama_analyses: int
    errors: List[str]
    timestamp: str

class TeamWorkload(BaseModel):
    user_id: int
    name: str
    max_tickets: Optional[int]
    current_tickets: int
    status: str  # available, at_capacity, unknown

class WorkloadResponse(BaseModel):
    l1_team: List[TeamWorkload]
    l2_team: List[TeamWorkload]
    business_hours: bool
    timestamp: str
