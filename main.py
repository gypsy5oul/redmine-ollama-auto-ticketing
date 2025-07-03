#!/usr/bin/env python3
"""
Enhanced DevOps Ticket Automation API
Main FastAPI application with Ollama integration and smart priority management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from datetime import datetime
import logging
from config import Config
from models import AutomationResponse, WorkloadResponse
from devops_service import DevOpsAutomationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the service
automation_service = DevOpsAutomationService()

# FastAPI App
app = FastAPI(
    title="Enhanced DevOps Ticket Automation API",
    description="""
    Intelligent DevOps ticket automation with:
    • Ollama AI analysis for professional responses
    • Smart priority management (P1 only for production)
    • Workload-based assignment to L1/L2 teams
    • Business hours awareness
    • Automatic ticket notes for priority adjustments
    """,
    version="2.0.0"
)

@app.get("/")
async def root():
    """API health check and information"""
    return {
        "service": "Enhanced DevOps Automation API",
        "version": "2.0.0",
        "status": "healthy",
        "features": [
            "Ollama AI Integration",
            "Smart Priority Management", 
            "Environment-based P1 filtering",
            "Workload-based Assignment",
            "Business Hours Awareness"
        ],
        "business_hours": automation_service.is_business_hours(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check for all components"""
    try:
        # Test Redmine connectivity
        redmine_status = "healthy"
        try:
            import requests
            response = requests.get(
                f"{Config.REDMINE_BASE_URL}/users/current.json",
                headers={'X-Redmine-API-Key': Config.REDMINE_API_KEY},
                timeout=5
            )
            if response.status_code != 200:
                redmine_status = f"unhealthy (HTTP {response.status_code})"
        except Exception as e:
            redmine_status = f"unreachable ({str(e)[:50]})"

        # Test Ollama connectivity
        ollama_result = automation_service.test_ollama_connection()
        ollama_status = "healthy" if ollama_result["success"] else f"unhealthy ({ollama_result.get('error', 'Unknown error')[:50]})"

        overall_status = "healthy" if redmine_status == "healthy" and ollama_status == "healthy" else "degraded"

        return {
            "service": "Enhanced DevOps Automation API",
            "overall_status": overall_status,
            "components": {
                "redmine": {
                    "status": redmine_status,
                    "url": Config.REDMINE_BASE_URL
                },
                "ollama": {
                    "status": ollama_status,
                    "url": Config.OLLAMA_BASE_URL,
                    "model": Config.OLLAMA_MODEL
                }
            },
            "configuration": {
                "business_hours": automation_service.is_business_hours(),
                "test_mode": Config.TEST_MODE,
                "l1_team_size": len(Config.L1_MEMBERS),
                "l2_team_size": len(Config.L2_MEMBERS)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "service": "Enhanced DevOps Automation API",
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/process-tickets", response_model=AutomationResponse)
async def process_tickets_endpoint():
    """
    🚀 MAIN ENDPOINT - Process all pending DevOps tickets with AI analysis
    
    This endpoint performs the complete automation pipeline:
    1. ✅ Fetches new DevOps tickets assigned to team group  
    2. 🔄 Adjusts priorities (P1 only for production environments)
    3. 🤖 Analyzes each ticket with Ollama AI for professional responses
    4. 👥 Assigns tickets to optimal L1/L2 team members based on workload
    5. 📝 Updates tickets in Redmine with AI analysis and assignment notes
    6. 📊 Returns comprehensive processing summary
    
    **New Features:**
    - Smart priority management (P1 downgraded to P2 for non-prod)
    - Ollama AI integration for intelligent initial responses
    - Detailed ticket notes explaining priority adjustments
    - Enhanced workload tracking (In Progress tickets only)
    """
    logger.info("🚀 Processing tickets endpoint called")
    try:
        result = automation_service.process_tickets()
        
        # Enhanced logging for monitoring
        if result.success:
            logger.info(f"✅ Endpoint Success: {result.total_processed} tickets, "
                       f"{result.priority_adjustments} priority adjustments, "
                       f"{result.ollama_analyses} AI analyses")
        else:
            logger.error(f"❌ Endpoint Failed: {len(result.errors)} errors")
            
        return result
        
    except Exception as e:
        logger.error(f"💥 Endpoint Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/team-workload", response_model=WorkloadResponse)
async def get_team_workload():
    """
    📊 Get current team workload (In Progress tickets only)
    
    Returns real-time workload information for capacity planning:
    - L1 team members with availability status
    - L2 team members with current load
    - Business hours status
    - Only counts "In Progress" tickets for accurate availability
    """
    try:
        workload_data = automation_service.get_team_workload()
        return WorkloadResponse(**workload_data)
        
    except Exception as e:
        logger.error(f"❌ Workload endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-ollama")
async def test_ollama_endpoint():
    """
    🤖 Test Ollama AI connectivity and model availability
    
    Performs comprehensive Ollama testing:
    - API connectivity check
    - Model availability verification  
    - Sample ticket analysis generation
    - Performance timing
    """
    try:
        result = automation_service.test_ollama_connection()
        
        if result["success"]:
            logger.info(f"✅ Ollama test successful: {Config.OLLAMA_MODEL}")
            return result
        else:
            logger.warning(f"⚠️ Ollama test failed: {result.get('error')}")
            raise HTTPException(status_code=503, detail=result)
            
    except Exception as e:
        logger.error(f"❌ Ollama test exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama test failed: {str(e)}")

@app.post("/enable-test-mode")
async def enable_test_mode():
    """🧪 Enable test mode with simulated data (for development)"""
    Config.TEST_MODE = True
    automation_service.config.TEST_MODE = True
    logger.info("🧪 Test mode enabled")
    
    return {
        "message": "Test mode enabled - using simulated tickets and workloads",
        "test_mode": True,
        "note": "This bypasses network calls to Redmine for safe testing",
        "sample_tickets": 2,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/disable-test-mode") 
async def disable_test_mode():
    """🔄 Disable test mode - use real Redmine API"""
    Config.TEST_MODE = False
    automation_service.config.TEST_MODE = False
    logger.info("🔄 Test mode disabled")
    
    return {
        "message": "Test mode disabled - using real Redmine API",
        "test_mode": False,
        "note": "Now connecting to live Redmine instance",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug-workload/{user_id}")
async def debug_user_workload(user_id: int):
    """🔍 Debug workload calculation for a specific user"""
    try:
        logger.info(f"🔍 Debugging workload for user {user_id}")
        
        # Test all methods
        methods_result = {}
        
        # Method 1: Status filter
        try:
            result1 = automation_service._get_workload_method_1(user_id)
            methods_result["method_1_status_filter"] = {
                "success": True,
                "workload": result1,
                "description": "Query with status_id=2"
            }
        except Exception as e:
            methods_result["method_1_status_filter"] = {
                "success": False,
                "error": str(e),
                "description": "Query with status_id=2"
            }

        # Method 2: Manual count
        try:
            result2 = automation_service._get_workload_method_2(user_id)
            methods_result["method_2_manual_count"] = {
                "success": True,
                "workload": result2,
                "description": "Get all tickets, count In Progress manually"
            }
        except Exception as e:
            methods_result["method_2_manual_count"] = {
                "success": False,
                "error": str(e),
                "description": "Get all tickets, count In Progress manually"
            }

        # Method 3: Alternative
        try:
            result3 = automation_service._get_workload_method_3(user_id)
            methods_result["method_3_alternative"] = {
                "success": True,
                "workload": result3,
                "description": "Query with status_id=open, filter by name"
            }
        except Exception as e:
            methods_result["method_3_alternative"] = {
                "success": False,
                "error": str(e),
                "description": "Query with status_id=open, filter by name"
            }

        # Final workload using the main method
        final_workload = automation_service.get_user_workload(user_id)
        
        # Get user info
        user_info = None
        for member in Config.L1_MEMBERS + Config.L2_MEMBERS:
            if member['user_id'] == user_id:
                user_info = member
                break

        return {
            "user_id": user_id,
            "user_info": user_info,
            "final_workload": final_workload,
            "methods_tested": methods_result,
            "timestamp": datetime.now().isoformat(),
            "note": "This helps diagnose workload calculation issues"
        }

    except Exception as e:
        logger.error(f"❌ Debug workload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@app.get("/config")
async def get_configuration():
    """⚙️ Get current service configuration (non-sensitive)"""
    return {
        "service": "Enhanced DevOps Automation",
        "redmine": {
            "base_url": Config.REDMINE_BASE_URL,
            "project_id": Config.DEVOPS_PROJECT_ID,
            "team_group_id": Config.DEVOPS_TEAM_GROUP_ID
        },
        "ollama": {
            "base_url": Config.OLLAMA_BASE_URL,
            "model": Config.OLLAMA_MODEL,
            "timeout": Config.OLLAMA_TIMEOUT
        },
        "team": {
            "l1_members": len(Config.L1_MEMBERS),
            "l2_members": len(Config.L2_MEMBERS),
            "l1_max_tickets": Config.L1_MEMBERS[0]["max_tickets"] if Config.L1_MEMBERS else None
        },
        "business_hours": Config.BUSINESS_HOURS,
        "critical_environments": Config.CRITICAL_ENVIRONMENTS,
        "test_mode": Config.TEST_MODE,
        "timestamp": datetime.now().isoformat()
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"💥 Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Enhanced DevOps Automation API...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
