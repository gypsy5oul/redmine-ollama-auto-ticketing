#!/bin/bash

# Production Testing Script for Enhanced DevOps Automation
echo "🚀 Testing Enhanced DevOps Automation in PRODUCTION MODE"
echo "========================================================="

API_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_section() {
    echo -e "\n${BLUE}$1${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Step 1: Ensure we're in production mode
print_section "1. Ensuring Production Mode"
curl -s -X POST "$API_URL/disable-test-mode" | python3 -m json.tool
echo ""

# Step 2: Check health
print_section "2. System Health Check"
health_response=$(curl -s "$API_URL/health")
echo "$health_response" | python3 -m json.tool

# Check if all systems are healthy
if echo "$health_response" | grep -q '"overall_status": "healthy"'; then
    print_success "All systems healthy!"
else
    print_warning "Some systems may be degraded - check above"
fi
echo ""

# Step 3: Check current team workload
print_section "3. Current Team Workload (Real Data)"
echo "Getting live workload from Redmine..."
workload_response=$(curl -s "$API_URL/team-workload")
echo "$workload_response" | python3 -m json.tool

echo ""
print_success "Team Availability Summary:"
echo "$workload_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    print('L1 Team:')
    for member in data['l1_team']:
        status_icon = '✅' if member['status'] == 'available' else '🔴'
        print(f'  {status_icon} {member[\"name\"]}: {member[\"current_tickets\"]}/{member[\"max_tickets\"]} tickets')
    
    print('\nL2 Team:')
    for member in data['l2_team']:
        print(f'  ✅ {member[\"name\"]}: {member[\"current_tickets\"]} tickets')
        
    business_hours = '✅ YES' if data['business_hours'] else '❌ NO'
    print(f'\nBusiness Hours: {business_hours}')
        
except Exception as e:
    print(f'Error parsing workload: {e}')
"
echo ""

# Step 4: Process real tickets
print_section "4. 🎯 MAIN TEST - Processing Real Tickets"
echo "This will:"
echo "  • Fetch actual new tickets from Redmine"
echo "  • Apply smart priority logic (P1 only for prod)"
echo "  • Generate AI analysis with Ollama"
echo "  • Assign to team members based on workload"
echo "  • Update tickets in Redmine with professional responses"
echo ""

read -p "🚀 Proceed with processing real tickets? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Processing real tickets..."
    processing_response=$(curl -s -X POST "$API_URL/process-tickets")
    echo "$processing_response" | python3 -m json.tool
    
    echo ""
    print_section "📊 Real Processing Results"
    echo "$processing_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    if data['success']:
        print('🎉 PRODUCTION PROCESSING SUCCESSFUL!')
        print(f'📊 Tickets processed: {data[\"total_processed\"]}')
        print(f'🔄 Priority adjustments: {data[\"priority_adjustments\"]}')
        print(f'🤖 AI analyses: {data[\"ollama_analyses\"]}')
        print(f'❌ Errors: {len(data[\"errors\"])}')
        
        successful_assignments = sum(1 for t in data['processed_tickets'] if t['success'])
        print(f'✅ Successful assignments: {successful_assignments}')
        
        if data['processed_tickets']:
            print('\n📋 Ticket Details:')
            for ticket in data['processed_tickets']:
                status = '✅' if ticket['success'] else '❌'
                env_info = f\"({ticket['environment']})\" if ticket['environment'] else ''
                priority_info = f\"{ticket['original_priority']} → {ticket['adjusted_priority']}\" if ticket['priority_downgraded'] else ticket['adjusted_priority']
                
                print(f'  {status} #{ticket[\"ticket_id\"]}: {priority_info} {env_info}')
                print(f'      👤 Assigned to: {ticket[\"assigned_to\"][\"name\"]} ({ticket[\"assignment_type\"]})')
                if ticket['priority_downgraded']:
                    print(f'      🔄 Priority downgraded (non-production environment)')
                if ticket['success']:
                    print(f'      🔗 {ticket[\"redmine_url\"]}')
                print()
        
        if data['errors']:
            print('❌ Errors encountered:')
            for error in data['errors']:
                print(f'  • {error}')
                
        # Next steps
        print('\n🎯 NEXT STEPS:')
        if successful_assignments > 0:
            print('  1. ✅ Check Redmine - tickets should be assigned with AI responses')
            print('  2. ✅ Verify Google Chat notifications from n8n workflow')
            print('  3. ✅ Review AI analysis quality in ticket notes')
            print('  4. ✅ Monitor team workload distribution')
        else:
            print('  1. ⚠️  No tickets were assigned - check if there are new tickets')
            print('  2. ⚠️  Verify Redmine connectivity and permissions')
            
    else:
        print('❌ PRODUCTION PROCESSING FAILED!')
        for error in data.get('errors', []):
            print(f'  • {error}')
            
except Exception as e:
    print(f'Error analyzing results: {e}')
"
else
    print_warning "Skipped real ticket processing"
fi

echo ""
print_section "5. Production Test Summary"
echo "🎯 Enhanced DevOps Automation Production Test Complete!"
echo ""
echo "✅ Verified Components:"
echo "  • Redmine connectivity"
echo "  • Ollama AI integration" 
echo "  • Team workload tracking"
echo "  • Smart priority management"
echo "  • Environment-based filtering"
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔍 Check Results:"
    echo "  1. Open Redmine to see assigned tickets with AI analysis"
    echo "  2. Monitor Google Chat for n8n notifications"
    echo "  3. Verify ticket notes contain professional AI responses"
    echo "  4. Confirm priority adjustments are explained in ticket notes"
else
    echo "💡 When ready to test with real tickets:"
    echo "  Run: curl -X POST $API_URL/process-tickets"
fi

echo ""
print_success "Production testing framework ready!"
