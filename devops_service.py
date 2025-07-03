#!/usr/bin/env python3
"""
Core DevOps Automation Service
Handles ticket processing, Ollama AI integration, and smart priority management
"""

import requests
import logging
from datetime import datetime
import pytz
from typing import List, Dict, Optional, Tuple
from config import Config
from models import ProcessedTicket, AutomationResponse, TicketAssignment, TeamWorkload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DevOpsAutomationService:
    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        self.session.headers.update({
            'X-Redmine-API-Key': self.config.REDMINE_API_KEY,
            'Content-Type': 'application/json'
        })
        logger.info("🚀 DevOps Automation Service initialized")

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        ist = pytz.timezone(self.config.BUSINESS_HOURS["timezone"])
        current_time = datetime.now(ist)
        current_hour = current_time.hour
        
        return (self.config.BUSINESS_HOURS["start"] <= 
                current_hour < 
                self.config.BUSINESS_HOURS["end"])

    def get_new_devops_tickets(self) -> List[Dict]:
        """Fetch new DevOps tickets assigned to team group"""
        if self.config.TEST_MODE:
            logger.info("🧪 TEST MODE: Returning simulated tickets")
            return [
                {
                    "id": 99991,
                    "subject": "Production database connection timeout",
                    "description": "Users unable to login - production database showing connection timeouts",
                    "priority": {"id": 4, "name": "P1(Critical)"},
                    "tracker": {"id": 3, "name": "General Support"},
                    "status": {"id": 1, "name": "New"},
                    "project": {"id": 1, "name": "Devops Support"},
                    "assigned_to": {"id": 6, "name": "DevOps Team"},
                    "custom_fields": [
                        {"name": "Project Jira ID", "value": "AUTH-SERVICE"},
                        {"name": "Deployment Environment Tags", "value": "prod"}
                    ]
                },
                {
                    "id": 99992,
                    "subject": "Development environment deployment failing",
                    "description": "CI/CD pipeline failing on dev environment - need assistance",
                    "priority": {"id": 4, "name": "P1(Critical)"},
                    "tracker": {"id": 3, "name": "General Support"},
                    "status": {"id": 1, "name": "New"},
                    "project": {"id": 1, "name": "Devops Support"},
                    "assigned_to": {"id": 6, "name": "DevOps Team"},
                    "custom_fields": [
                        {"name": "Project Jira ID", "value": "PAYMENT-SERVICE"},
                        {"name": "Deployment Environment Tags", "value": "dev"}
                    ]
                }
            ]

        try:
            url = f"{self.config.REDMINE_BASE_URL}/issues.json"
            params = {
                "project_id": self.config.DEVOPS_PROJECT_ID,
                "status_id": 1,  # New status
                "assigned_to_id": self.config.DEVOPS_TEAM_GROUP_ID,
                "limit": 50
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            tickets = data.get('issues', [])
            
            logger.info(f"📋 Found {len(tickets)} new DevOps tickets")
            return tickets

        except Exception as e:
            logger.error(f"❌ Error fetching tickets: {e}")
            return []

    def analyze_priority_and_environment(self, ticket: Dict) -> Tuple[str, str, str, bool, int]:
        """
        Analyze ticket priority and environment, adjust if needed
        Returns: (original_priority, adjusted_priority, environment, was_downgraded, new_priority_id)
        """
        original_priority = ticket['priority']['name']
        original_priority_id = ticket['priority']['id']
        custom_fields = {cf['name']: cf.get('value', '') for cf in ticket.get('custom_fields', [])}
        environment = custom_fields.get('Deployment Environment Tags', '').lower().strip()
        
        # Priority ID mapping for Redmine
        PRIORITY_IDS = {
            'P1(Critical)': 4,
            'P2(High)': 5,
            'P3(Medium)': 3,
            'P4(Low)': 2,
            'P5(Trivial)': 1
        }
        
        # Check if this is a true critical ticket (P1 + production environment)
        if original_priority == 'P1(Critical)':
            is_production = any(env in environment for env in self.config.CRITICAL_ENVIRONMENTS)
            
            if not is_production:
                # Downgrade P1 to P2 for non-production
                adjusted_priority = 'P2(High)'
                new_priority_id = PRIORITY_IDS['P2(High)']
                was_downgraded = True
                logger.info(f"🔄 Ticket #{ticket['id']}: P1→P2 downgrade (Environment: '{environment}' is not production)")
            else:
                adjusted_priority = original_priority
                new_priority_id = original_priority_id
                was_downgraded = False
                logger.info(f"✅ Ticket #{ticket['id']}: P1 maintained (Production environment: '{environment}')")
        else:
            adjusted_priority = original_priority
            new_priority_id = original_priority_id
            was_downgraded = False

        return original_priority, adjusted_priority, environment, was_downgraded, new_priority_id

    def get_user_workload(self, user_id: int) -> int:
        """Get current ticket count for a user with comprehensive error handling"""
        if self.config.TEST_MODE:
            test_workloads = {
                1239: 1, 1330: 3, 1329: 0, 1328: 4, 1327: 2, 
                1155: 1, 1795: 3, 21: 5, 155: 3, 11: 2, 10: 4
            }
            workload = test_workloads.get(user_id, 0)
            logger.info(f"🧪 TEST: User {user_id} workload: {workload} tickets")
            return workload

        # Try multiple approaches to get accurate workload
        methods = [
            self._get_workload_method_1,  # Status filter approach
            self._get_workload_method_2,  # No status filter, manual count
            self._get_workload_method_3   # Alternative API approach
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                workload = method(user_id)
                if workload is not None:
                    logger.debug(f"👤 User {user_id}: {workload} tickets (method {i})")
                    return workload
            except Exception as e:
                logger.debug(f"⚠️ Method {i} failed for user {user_id}: {e}")
                continue
        
        # All methods failed - return safe default
        logger.warning(f"⚠️ All workload methods failed for user {user_id}, returning 999 (overloaded)")
        return 999  # Force this user to be considered overloaded

    def _get_workload_method_1(self, user_id: int) -> Optional[int]:
        """Method 1: Query with status filter"""
        url = f"{self.config.REDMINE_BASE_URL}/issues.json"
        params = {
            "assigned_to_id": user_id,
            "status_id": "2",  # In Progress only
            "limit": 100
        }
        
        response = self.session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('total_count', 0)
        else:
            raise Exception(f"HTTP {response.status_code}")

    def _get_workload_method_2(self, user_id: int) -> Optional[int]:
        """Method 2: Get all tickets and count manually"""
        url = f"{self.config.REDMINE_BASE_URL}/issues.json"
        params = {
            "assigned_to_id": user_id,
            "limit": 100
        }
        
        response = self.session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Count tickets with status_id = 2 (In Progress)
            in_progress_count = sum(1 for issue in data.get('issues', [])
                                  if issue.get('status', {}).get('id') == 2)
            return in_progress_count
        else:
            raise Exception(f"HTTP {response.status_code}")

    def _get_workload_method_3(self, user_id: int) -> Optional[int]:
        """Method 3: Alternative query approach"""
        url = f"{self.config.REDMINE_BASE_URL}/issues.json"
        params = {
            "assigned_to_id": user_id,
            "status_id": "open",  # Try open status
            "limit": 100
        }
        
        response = self.session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Count only In Progress tickets
            in_progress_count = sum(1 for issue in data.get('issues', [])
                                  if issue.get('status', {}).get('name', '').lower() == 'in progress')
            return in_progress_count
        else:
            raise Exception(f"HTTP {response.status_code}")

    def find_best_assignee(self, adjusted_priority: str, is_business_hours: bool) -> Optional[Dict]:
        """Find the best team member based on adjusted priority and workload"""
        
        if adjusted_priority == 'P1(Critical)':
            # True P1 (production) - always L2 team (24/7 support)
            try:
                best_l2 = min(self.config.L2_MEMBERS, 
                             key=lambda m: self.get_user_workload(m['user_id']))
                workload = self.get_user_workload(best_l2['user_id'])
                
                return {
                    **best_l2,
                    "assignment_type": "L2_CRITICAL_PROD",
                    "reason": f"P1 Critical PRODUCTION issue - L2 team (24/7) - Current load: {workload} tickets"
                }
            except Exception as e:
                logger.error(f"❌ Error finding L2 assignee: {e}")
                return self.config.L2_MEMBERS[0]

        elif is_business_hours:
            # P2-P5 during business hours - try L1 first
            available_l1 = []
            
            for member in self.config.L1_MEMBERS:
                current_load = self.get_user_workload(member['user_id'])
                if current_load < member['max_tickets']:
                    available_l1.append((member, current_load))

            if available_l1:
                # Assign to L1 member with lowest workload
                best_l1, current_load = min(available_l1, key=lambda x: x[1])
                return {
                    **best_l1,
                    "assignment_type": "L1_BUSINESS_HOURS",
                    "reason": f"P2-P5 during business hours - L1 team - Load: {current_load}/{best_l1['max_tickets']}"
                }
            else:
                # All L1 at capacity, escalate to L2
                try:
                    best_l2 = min(self.config.L2_MEMBERS, 
                                 key=lambda m: self.get_user_workload(m['user_id']))
                    workload = self.get_user_workload(best_l2['user_id'])
                    
                    return {
                        **best_l2,
                        "assignment_type": "L2_L1_OVERLOADED",
                        "reason": f"L1 team at capacity (5+ tickets each) - Escalated to L2 - Load: {workload}"
                    }
                except Exception as e:
                    logger.error(f"❌ Error finding L2 backup: {e}")
                    return self.config.L2_MEMBERS[0]
        else:
            # Outside business hours - non-critical tickets wait
            return None

    def analyze_with_ollama(self, ticket: Dict, environment: str, priority: str) -> str:
        """Enhanced Ollama analysis with professional structured information requests"""
        try:
            custom_fields = {cf['name']: cf.get('value', '') for cf in ticket.get('custom_fields', [])}
            project_id = custom_fields.get('Project Jira ID', 'Unknown')
            
            # Enhanced professional prompt with structured information requests
            prompt = f"""Act as a professional DevOps Engineer specializing in Kubernetes, GitLab CI/CD pipelines, and utility services such as RabbitMQ, Redis, Kafka, Elasticsearch, and NiFi. Provide a structured response similar to enterprise support portals like RedHat.

## Ticket Information
- ID: #{ticket['id']}
- Subject: {ticket['subject']}
- Description: {ticket.get('description', 'No description provided')}
- Priority: {priority}
- Environment: {environment.upper() if environment else 'Not specified'}
- Project: {project_id}

## Response Requirements
Generate a professional support response with the following structure:

1. **Acknowledgment** - Brief professional acknowledgment
2. **Initial Assessment** - Technology category and potential impact
3. **Information Required** - Structured bullet points requesting specific details
4. **Troubleshooting Commands** - Relevant diagnostic commands if applicable
5. **Next Steps** - Clear process for resolution

## Information Request Format
Use this EXACT format for requesting information:

**To assist in resolving this issue efficiently, please provide the following information:**

1. **Business Impact:** Does this affect business operations, end users, or revenue?
2. **Error Details:** Please provide any error messages, logs, or specific symptoms observed.

## Technical Commands Format
If the issue relates to specific technologies, provide relevant diagnostic commands:
- For Kubernetes: kubectl commands
- For message brokers: status and log commands  
- For databases: connection and performance checks
- For CI/CD: pipeline and build diagnostics

Keep the response professional, structured, and under 300 words. Focus on information gathering rather than immediate solutions."""

            url = f"{self.config.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": self.config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }

            logger.info(f"🤖 Requesting professional structured analysis for ticket #{ticket['id']}")
            response = requests.post(url, json=payload, timeout=self.config.OLLAMA_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('response', '').strip()
                
                if analysis:
                    logger.info(f"✅ Professional structured analysis completed for ticket #{ticket['id']} ({len(analysis)} chars)")
                    return analysis
                else:
                    logger.warning(f"⚠️ Empty Ollama response for ticket #{ticket['id']}")
                    
            else:
                logger.warning(f"⚠️ Ollama API error for ticket #{ticket['id']}: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Ollama timeout for ticket #{ticket['id']} ({self.config.OLLAMA_TIMEOUT}s)")
        except Exception as e:
            logger.warning(f"⚠️ Ollama error for ticket #{ticket['id']}: {e}")

        # Enhanced fallback analysis with structured format
        return self._generate_professional_fallback_analysis(ticket, environment, priority)

    def _generate_professional_fallback_analysis(self, ticket: Dict, environment: str, priority: str) -> str:
        """Professional fallback analysis with structured information requests like enterprise support portals"""
        subject_lower = ticket.get('subject', '').lower()
        description_lower = ticket.get('description', '').lower()
        combined_text = subject_lower + ' ' + description_lower
        
        # Enhanced categorization with specific technologies
        if any(word in combined_text for word in ['kubernetes', 'k8s', 'pod', 'deployment', 'namespace']):
            category = "Kubernetes Infrastructure"
            commands = [
                "kubectl get pods -n <namespace>",
                "kubectl describe pod <pod_name> -n <namespace>", 
                "kubectl logs <pod_name> -n <namespace> --tail=100"
            ]
            
        elif any(word in combined_text for word in ['rabbitmq', 'rabbit', 'mq', 'queue', 'message']):
            category = "RabbitMQ Message Broker"
            commands = [
                "kubectl logs <rabbitmq-pod-name> --tail=100",
                "kubectl exec -it <rabbitmq-pod> -- rabbitmqctl status",
                "kubectl exec -it <rabbitmq-pod> -- rabbitmqctl list_queues"
            ]
            
        elif any(word in combined_text for word in ['redis', 'cache', 'session']):
            category = "Redis Cache Service"  
            commands = [
                "kubectl logs <redis-pod-name> --tail=100",
                "kubectl exec -it <redis-pod> -- redis-cli ping",
                "kubectl exec -it <redis-pod> -- redis-cli info memory"
            ]
            
        elif any(word in combined_text for word in ['kafka', 'streaming', 'topic']):
            category = "Kafka Streaming Platform"
            commands = [
                "kubectl logs <kafka-pod-name> --tail=100",
                "kubectl exec -it <kafka-pod> -- kafka-topics --list"
            ]
            
        elif any(word in combined_text for word in ['elasticsearch', 'elastic', 'search']):
            category = "Elasticsearch Search Engine"
            commands = [
                "kubectl logs <elasticsearch-pod-name> --tail=100",
                "kubectl exec -it <es-pod> -- curl -X GET 'localhost:9200/_cluster/health'"
            ]
            
        elif any(word in combined_text for word in ['gitlab', 'ci/cd', 'pipeline', 'build']):
            category = "GitLab CI/CD Pipeline"
            commands = [
                "kubectl logs <gitlab-runner-pod> --tail=100",
                "kubectl get pods -l app=gitlab-runner"
            ]
            
        elif any(word in combined_text for word in ['database', 'db', 'sql', 'mysql', 'postgres']):
            category = "Database Service"
            commands = [
                "kubectl logs <database-pod-name> --tail=100",
                "kubectl describe pod <database-pod-name>"
            ]
            
        else:
            category = "Infrastructure Service"
            commands = [
                "kubectl get pods --all-namespaces",
                "kubectl get events --sort-by=.metadata.creationTimestamp"
            ]

        env_context = f" in the {environment.upper()} environment" if environment else ""
        
        return f"""Thank you for contacting 6D DevOps Support regarding this {category.lower()} issue{env_context}.

**Initial Assessment:**
This appears to be a {category} issue that requires additional information for proper diagnosis and resolution.

**To assist in resolving this issue efficiently, please provide the following information:**

1. **Error Details:** Please provide any error messages, logs, or specific symptoms observed.
2. **Recent Changes:** Were there any recent deployments, configuration changes, or updates?
3. **Issue Description: 

**Diagnostic Commands:**
Please run the following commands and provide the output:

```
{chr(10).join(commands)}
```

**Next Steps:**
Once we receive this information, our team will perform a comprehensive analysis and provide specific resolution steps. This structured approach ensures efficient problem resolution.

*Note: This response was generated by our automated triage system. Our AI analysis service will provide enhanced diagnostics once connectivity is restored.*"""

    def add_priority_downgrade_note(self, ticket_id: int, environment: str, new_priority_id: int) -> bool:
        """Add a clean, professional note explaining priority adjustment"""
        try:
            url = f"{self.config.REDMINE_BASE_URL}/issues/{ticket_id}.json"
            
            # Clean, professional downgrade note
            downgrade_note = f"""Priority Adjustment Notice

This ticket priority has been adjusted from P1 (Critical) to P2 (High) based on our incident management policy.

Reason: Non-production environment issue
Environment: {environment or "Not specified"}
Policy: P1 (Critical) priority is reserved for production environment incidents that directly impact end users and business operations.

This adjustment ensures our critical incident response resources are properly allocated to production emergencies while maintaining appropriate priority for development and testing environment issues.

If this issue affects production services or has critical business impact, please:
1. Add a comment explaining the production impact
2. Contact the DevOps team directly for immediate escalation

---
DevOps Priority Management
{datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}"""

            payload = {
                "issue": {
                    "priority_id": new_priority_id,  # Actually update the priority in Redmine
                    "notes": downgrade_note
                }
            }

            response = self.session.put(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"📝 Added clean priority adjustment note to ticket #{ticket_id} and updated priority to ID {new_priority_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add priority adjustment note to ticket #{ticket_id}: {e}")
            return False

    def assign_ticket_in_redmine(self, ticket_id: int, assignee: Dict, ai_analysis: str) -> bool:
        """Assign ticket with AI analysis and change status to In Progress"""
        try:
            url = f"{self.config.REDMINE_BASE_URL}/issues/{ticket_id}.json"

            assignment_note = f"""🎫 DEVOPS TICKET ASSIGNMENT


AI ANALYSIS & INITIAL RESPONSE:
{ai_analysis}

NEXT STEPS:
• Your SPOC will investigate and provide updates
• Add any additional information as comments
• Contact your assigned SPOC via Google Chat for urgent matters

System: DevOps Automation with AI Analysis
Timestamp: {datetime.now().isoformat()}"""

            payload = {
                "issue": {
                    "assigned_to_id": assignee['user_id'],
                    "status_id": 2,  # Change status to "In Progress"
                    "notes": assignment_note
                }
            }

            response = self.session.put(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"✅ Successfully assigned ticket #{ticket_id} to {assignee['name']} with AI analysis")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to assign ticket #{ticket_id}: {e}")
            return False

    def process_tickets(self) -> AutomationResponse:
        """Main ticket processing pipeline with Ollama AI integration"""
        start_time = datetime.now()
        processed_tickets = []
        errors = []
        priority_adjustments = 0
        ollama_analyses = 0

        try:
            logger.info("🚀 Starting ticket processing pipeline...")
            
            # 1. Fetch new tickets
            tickets = self.get_new_devops_tickets()
            if not tickets:
                logger.info("📭 No new tickets found")
                return AutomationResponse(
                    success=True, processed_tickets=[], total_processed=0,
                    priority_adjustments=0, ollama_analyses=0,
                    errors=["No new tickets found"], timestamp=start_time.isoformat()
                )

            # 2. Process each ticket through the complete pipeline
            is_business_hours = self.is_business_hours()
            logger.info(f"⏰ Business hours: {'Yes' if is_business_hours else 'No'}")

            for ticket in tickets:
                try:
                    logger.info(f"\n🎫 Processing ticket #{ticket['id']}: {ticket['subject'][:50]}...")

                    # 3. Analyze and adjust priority based on environment
                    original_priority, adjusted_priority, environment, was_downgraded, new_priority_id = \
                        self.analyze_priority_and_environment(ticket)

                    if was_downgraded:
                        priority_adjustments += 1
                        # Add explanatory note AND update priority in Redmine
                        self.add_priority_downgrade_note(ticket['id'], environment, new_priority_id)

                    # 4. Find best assignee based on adjusted priority
                    assignee = self.find_best_assignee(adjusted_priority, is_business_hours)
                    
                    if not assignee:
                        # Outside business hours for non-critical tickets
                        logger.info(f"⏸️ Ticket #{ticket['id']} waiting for business hours")
                        processed_tickets.append(ProcessedTicket(
                            ticket_id=ticket['id'], subject=ticket['subject'],
                            original_priority=original_priority, adjusted_priority=adjusted_priority,
                            environment=environment, priority_downgraded=was_downgraded,
                            assigned_to=TicketAssignment(user_id=0, name="Pending"),
                            assignment_type="OUTSIDE_HOURS", 
                            reason="Non-critical ticket outside business hours (9AM-9PM IST)",
                            ai_analysis="Waiting for business hours", ai_analysis_short="Pending business hours",
                            redmine_url=f"{self.config.REDMINE_BASE_URL}/issues/{ticket['id']}",
                            success=True
                        ))
                        continue

                    # 5. **OLLAMA AI ANALYSIS** - This is now actually used!
                    logger.info(f"🤖 Generating AI analysis for ticket #{ticket['id']}")
                    ai_analysis = self.analyze_with_ollama(ticket, environment, adjusted_priority)
                    ollama_analyses += 1

                    # 6. Assign ticket in Redmine with AI analysis
                    assignment_success = self.assign_ticket_in_redmine(ticket['id'], assignee, ai_analysis)

                    # 7. Record processing result
                    processed_tickets.append(ProcessedTicket(
                        ticket_id=ticket['id'], subject=ticket['subject'],
                        original_priority=original_priority, adjusted_priority=adjusted_priority,
                        environment=environment, priority_downgraded=was_downgraded,
                        assigned_to=TicketAssignment(
                            user_id=assignee['user_id'], name=assignee['name'],
                            max_tickets=assignee.get('max_tickets')
                        ),
                        assignment_type=assignee['assignment_type'], reason=assignee['reason'],
                        ai_analysis=ai_analysis, ai_analysis_short="AI analysis with SPOC assignment",
                        redmine_url=f"{self.config.REDMINE_BASE_URL}/issues/{ticket['id']}",
                        success=assignment_success,
                        error=None if assignment_success else "Failed to assign in Redmine"
                    ))

                    if assignment_success:
                        logger.info(f"✅ COMPLETED: #{ticket['id']} → {assignee['name']} "
                                  f"({assignee['assignment_type']}) with AI analysis")
                    else:
                        logger.error(f"❌ FAILED: Could not assign #{ticket['id']}")

                except Exception as e:
                    error_msg = f"Error processing ticket #{ticket['id']}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)

            # 8. Summary
            successful = len([t for t in processed_tickets if t.success])
            logger.info(f"\n📊 PROCESSING SUMMARY:")
            logger.info(f"   Total tickets: {len(processed_tickets)}")
            logger.info(f"   Successfully assigned: {successful}")
            logger.info(f"   Priority adjustments: {priority_adjustments}")
            logger.info(f"   AI analyses: {ollama_analyses}")
            logger.info(f"   Errors: {len(errors)}")

            return AutomationResponse(
                success=True, processed_tickets=processed_tickets,
                total_processed=len(processed_tickets), priority_adjustments=priority_adjustments,
                ollama_analyses=ollama_analyses, errors=errors,
                timestamp=start_time.isoformat()
            )

        except Exception as e:
            error_msg = f"Critical error in process_tickets: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return AutomationResponse(
                success=False, processed_tickets=processed_tickets,
                total_processed=len(processed_tickets), priority_adjustments=priority_adjustments,
                ollama_analyses=ollama_analyses, errors=[error_msg] + errors,
                timestamp=start_time.isoformat()
            )

    def get_team_workload(self) -> Dict:
        """Get current workload for all team members"""
        try:
            l1_workload = []
            for member in self.config.L1_MEMBERS:
                try:
                    current_tickets = self.get_user_workload(member['user_id'])
                    status = "available" if current_tickets < member['max_tickets'] else "at_capacity"
                except:
                    current_tickets = 0
                    status = "unknown"

                l1_workload.append(TeamWorkload(
                    user_id=member['user_id'], name=member['name'],
                    max_tickets=member['max_tickets'], current_tickets=current_tickets,
                    status=status
                ))

            l2_workload = []
            for member in self.config.L2_MEMBERS:
                try:
                    current_tickets = self.get_user_workload(member['user_id'])
                    status = "available"
                except:
                    current_tickets = 0
                    status = "unknown"

                l2_workload.append(TeamWorkload(
                    user_id=member['user_id'], name=member['name'],
                    max_tickets=None, current_tickets=current_tickets,
                    status=status
                ))

            return {
                "l1_team": l1_workload,
                "l2_team": l2_workload,
                "business_hours": self.is_business_hours(),
                "timestamp": datetime.now().isoformat(),
                "note": "Workload shows only 'In Progress' tickets (status_id=2)"
            }

        except Exception as e:
            logger.error(f"❌ Error getting team workload: {e}")
            raise Exception(f"Failed to get team workload: {str(e)}")

    def test_ollama_connection(self) -> Dict:
        """Test Ollama connectivity and model availability"""
        try:
            # Test basic connectivity
            response = requests.get(f"{self.config.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Ollama API unreachable: HTTP {response.status_code}",
                    "endpoint": self.config.OLLAMA_BASE_URL
                }

            # Test model availability
            models = response.json().get('models', [])
            model_names = [model.get('name', '') for model in models]
            
            if self.config.OLLAMA_MODEL not in model_names:
                return {
                    "success": False,
                    "error": f"Model '{self.config.OLLAMA_MODEL}' not found",
                    "available_models": model_names,
                    "endpoint": self.config.OLLAMA_BASE_URL
                }

            # Test actual generation with sample ticket
            test_ticket = {
                "id": 99999,
                "subject": "Test connectivity to Ollama service",
                "description": "This is a connectivity test for the Ollama AI integration",
                "priority": {"name": "P3(Medium)"}
            }

            analysis = self.analyze_with_ollama(test_ticket, "test", "P3(Medium)")
            
            return {
                "success": True,
                "endpoint": self.config.OLLAMA_BASE_URL,
                "model": self.config.OLLAMA_MODEL,
                "available_models": model_names,
                "test_analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Ollama connection failed: {str(e)}",
                "endpoint": self.config.OLLAMA_BASE_URL
            }
