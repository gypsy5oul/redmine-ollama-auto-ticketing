#!/usr/bin/env python3
"""
Configuration Management for DevOps Automation
"""

import os
from typing import List, Dict

class Config:
    # Redmine Configuration
    REDMINE_BASE_URL = os.getenv("REDMINE_BASE_URL", "https://techsupport.6dtech.co.in")
    REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "fc4001d749bb08ed94ab48cd5b0e2b17f5add017")
    DEVOPS_PROJECT_ID = int(os.getenv("DEVOPS_PROJECT_ID", 1))
    DEVOPS_TEAM_GROUP_ID = int(os.getenv("DEVOPS_TEAM_GROUP_ID", 6))

    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://10.0.2.121:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 90))

    # Application Settings
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
    
    # Business Hours Configuration
    BUSINESS_HOURS = {
        "start": int(os.getenv("BUSINESS_START_HOUR", 9)),
        "end": int(os.getenv("BUSINESS_END_HOUR", 21)),
        "timezone": os.getenv("TIMEZONE", "Asia/Kolkata")
    }

    # Team Configuration
    L1_MEMBERS = [
        {"user_id": 1239, "name": "Shashikiran Umakanth", "max_tickets": 5},
        {"user_id": 1330, "name": "Jon Joseph", "max_tickets": 5},
        {"user_id": 1329, "name": "Lakshmi A B", "max_tickets": 5},
        {"user_id": 1328, "name": "Musab Acharath", "max_tickets": 5},
        {"user_id": 1327, "name": "Afsana ashraf", "max_tickets": 5},
        {"user_id": 1155, "name": "Sreehari Padmakumar", "max_tickets": 5},
        {"user_id": 1795, "name": "Joel Mathew", "max_tickets": 5}
    ]

    L2_MEMBERS = [
        {"user_id": 21, "name": "Arun Ramdas"},
        {"user_id": 155, "name": "Manoja Ningaraja"},
        {"user_id": 11, "name": "Jerish Vijay"},
        {"user_id": 10, "name": "Angel Varghese"}
    ]

    # Priority Settings
    CRITICAL_ENVIRONMENTS = ["prod", "production", "live"]
    PRIORITY_DOWNGRADE_NOTE = """
⚠️ PRIORITY ADJUSTMENT NOTICE:

This ticket was originally submitted as P1 (Critical) but has been automatically downgraded to P2 (High) because:

• Environment: {environment}
• Policy: Only production environment issues qualify for P1 Critical priority
• Impact: Non-production environments are handled with P2 priority during business hours

If this is genuinely a critical production issue, please:
1. Update the 'Deployment Environment Tags' field to specify 'prod'
2. Add a comment explaining the production impact
3. Contact the DevOps team directly for immediate escalation

This adjustment ensures our critical incident response is reserved for actual production emergencies.

System: Automated Priority Management
Timestamp: {timestamp}
"""
