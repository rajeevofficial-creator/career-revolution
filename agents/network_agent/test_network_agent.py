"""
Test script for Network Agent
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Adjust the path to import the agent correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from network_agent.network_agent import NetworkAgent, ConnectionType, ConnectionStrength
sys.path.pop(0)

def test_network_agent_workflow():
    """Test the complete workflow of the Network Agent."""
    print("Testing Network Agent Complete Workflow...")
    print("=" * 60)
    
    # Ensure the shared_data/profile directory exists for profile loading
    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'profile'))
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create a dummy master_profile.json if it doesn't exist for testing
    profile_path = os.path.join(profile_dir, "master_profile.json")
    if not os.path.exists(profile_path):
        dummy_profile_content = {
            "skills": {"detailed": {"technical": ["Cloud Computing", "Cybersecurity"], "management": ["Strategic Planning"]}},
            "experience": {"max_years": 18},
            "industries": {"primary": "finance_it"}
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_profile_content, f, indent=2)
        print(f"Created dummy profile data at {profile_path}")

    # Create test output directory
    test_output = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'network_test_agent'))
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize agent with test output
    agent = NetworkAgent(
        profile_data_path=profile_path,
        output_path=test_output
    )
    
    # Run complete workflow
    print("\nRunning complete network analysis and outreach workflow...")
    results = agent.run_complete_workflow()
    
    print(f"\nWorkflow Results:")
    print(f"  Connections analyzed: {results['connections_analyzed']}")
    print(f"  High-value connections: {results['high_value_connections']}")
    print(f"  Outreach messages: {results['outreach_messages']}")
    print(f"  Report file: {results['report_file']}")
    
    # Verify files were created
    print("\nVerifying generated files...")
    assert results['connections_analyzed'] > 0
    assert results['high_value_connections'] > 0
    # Outreach messages might be 0 if no high-value connections were identified for campaign
    assert os.path.exists(results['report_file'])
    
    print("\nComplete workflow test finished successfully!")
    return True

if __name__ == "__main__":
    try:
        test_network_agent_workflow()
    except Exception as e:
        print(f"\nError during Network Agent testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)