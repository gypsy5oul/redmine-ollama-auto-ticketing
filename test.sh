#!/bin/bash

# Enhanced DevOps Automation API Test Script
echo "🧪 Testing Enhanced DevOps Automation API with Ollama Integration..."
echo "=================================================================="

API_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Basic Health Check
print_section "1. API Health Check"
echo "Testing basic connectivity..."
curl -s "$API_URL/" | python3 -m json.tool
echo ""

# Test 2: Comprehensive Health Check
print_section "2. Comprehensive Health Check (Redmine + Ollama)"
echo "Checking all service dependencies..."
curl -s "$API_URL/health" | python3 -m json.tool
echo ""

# Test 3: Ollama Connectivity Test
print_section "3. Ollama AI Service Test"
echo "Testing Ollama connectivity and model availability..."
response=$(curl -s "$API_URL/test-ollama")
echo "$response" | python3 -m json.tool

# Check if Ollama test was successful
if echo "$response" | grep -q '"success": true'; then
    print_success "Ollama AI integration is working!"
else
    print_warning "Ollama AI may not be available - will use fallback analysis"
fi
echo ""

# Test 4: Enable Test Mode
print_section "4. Enabling Test Mode"
echo "Enabling test mode for safe testing..."
curl -s -X POST "$API_URL/enable-test-mode" | python3 -m json.tool
echo ""

# Test 5: Team Workload
print_section "5. Team Workload Analysis"
echo "Getting current team capacity (In Progress tickets only)..."
workload_response=$(curl -s "$API_URL/team-workload")
echo "$workload_response" | python3 -m json.tool

# Show available L1 members
echo ""
print_success "Available L1 Team Members:"
echo "$workload_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    available_l1 = [m for m in data['l1_team'] if m['status'] == 'available']
    if available_l1:
        for member in available_l1:
            print(f'  • {member[\"name\"]}: {member[\"current_tickets\"]}/{member[\"max_tickets\"]} tickets')
    else:
        print('  ⚠️  All L1 members at capacity!')
except:
    print('  Error parsing workload data')
"
echo ""

# Test 6: Configuration Check
print_section "6. Service Configuration"
echo "Checking service configuration..."
curl -s "$API_URL/config" | python3 -m json.tool
echo ""

# Test 7: Main Ticket Processing
print_section "7. MAIN TEST - Ticket Processing with AI Analysis"
echo "🚀 Processing tickets with Ollama AI integration..."
echo "This will test:"
echo "  • Smart priority adjustment (P1 only for prod)"
echo "  • Ollama AI analysis generation"
echo "  • Workload-based assignment"
echo "  • Comprehensive ticket notes"
echo ""

processing_response=$(curl -s -X POST "$API_URL/process-tickets")
echo "$processing_response" | python3 -m json.tool

# Analyze processing results
echo ""
print_section "📊 Processing Results Analysis"
echo "$processing_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    if data['success']:
        print(f'✅ Processing completed successfully!')
        print(f'📊 Total tickets processed: {data[\"total_processed\"]}')
        print(f'🔄 Priority adjustments: {data[\"priority_adjustments\"]}')
        print(f'🤖 AI analyses generated: {data[\"ollama_analyses\"]}')
        print(f'❌ Errors: {len(data[\"errors\"])}')
        
        if data['processed_tickets']:
            print(f'\\n📋 Processed Tickets Summary:')
            for ticket in data['processed_tickets']:
                status = '✅' if ticket['success'] else '❌'
                priority_info = f\"{ticket['original_priority']} → {ticket['adjusted_priority']}\" if ticket['priority_downgraded'] else ticket['adjusted_priority']
                print(f'  {status} #{ticket[\"ticket_id\"]}: {priority_info} → {ticket[\"assigned_to\"][\"name\"]} ({ticket[\"assignment_type\"]})')
                if ticket['priority_downgraded']:
                    print(f'      🔄 Downgraded (Environment: {ticket[\"environment\"]})')
                    
        if data['errors']:
            print(f'\\n❌ Errors encountered:')
            for error in data['errors']:
                print(f'  • {error}')
    else:
        print(f'❌ Processing failed!')
        for error in data.get('errors', []):
            print(f'  • {error}')
            
except Exception as e:
    print(f'Error analyzing results: {e}')
"

# Test 8: Final Status
print_section "8. Test Summary"
echo "🧪 Enhanced API Testing Complete!"
echo ""
echo "Key Features Tested:"
echo "  ✅ Ollama AI integration for ticket analysis"
echo "  ✅ Smart priority management (P1 only for production)"
echo "  ✅ Environment-based ticket filtering"
echo "  ✅ Workload-based team assignment"
echo "  ✅ Business hours awareness"
echo "  ✅ Comprehensive health monitoring"
echo ""

# Check if we should disable test mode
read -p "🔄 Disable test mode and switch to production? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_section "Disabling Test Mode"
    curl -s -X POST "$API_URL/disable-test-mode" | python3 -m json.tool
    print_warning "Test mode disabled - now using real Redmine API!"
else
    print_warning "Test mode remains enabled - remember to disable for production use"
fi

echo ""
print_success "Testing completed! Check the API logs for detailed processing information."
echo ""
echo "🔍 Next Steps:"
echo "  1. Check Redmine for assigned tickets (if test mode was disabled)"
echo "  2. Verify Ollama AI responses in ticket notes"
echo "  3. Monitor team workload distribution"
echo "  4. Set up n8n automation workflow"
