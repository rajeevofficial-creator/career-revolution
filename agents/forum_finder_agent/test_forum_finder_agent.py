"""
Test script for Forum Finder Agent
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Adjust the path to import the agent correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from forum_finder_agent.forum_finder_agent import ForumFinderAgent, EventType, EventStatus
sys.path.pop(0)

def test_forum_finder_agent_workflow():
    """Test the complete workflow of the Forum Finder Agent."""
    print("Testing Forum Finder Agent Complete Workflow...")
    print("=" * 60)
    
    # Ensure the shared_data/profile directory exists for profile loading
    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'profile'))
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create a dummy master_profile.json if it doesn't exist for testing
    profile_path = os.path.join(profile_dir, "master_profile.json")
    if not os.path.exists(profile_path):
        dummy_profile_content = {
            "skills": {"detailed": {"technical": ["AI", "Machine Learning"], "management": ["Project Management"]}},
            "experience": {"max_years": 12},
            "industries": {"primary": "pharma_it"}
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_profile_content, f, indent=2)
        print(f"Created dummy profile data at {profile_path}")

    # Create test output directory
    test_output = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'network_test'))
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize agent with test output
    agent = ForumFinderAgent(
        profile_data_path=profile_path,
        output_path=test_output
    )
    
    # Run complete workflow
    print("\nRunning complete event discovery and proposal workflow...")
    results = agent.run_complete_workflow()
    
    print(f"\nWorkflow Results:")
    print(f"  Events discovered: {results['events_discovered']}")
    print(f"  Events recommended: {results['events_recommended']}")
    print(f"  Proposals created: {results['proposals_created']}")
    print(f"  Scripts generated: {results['scripts_generated']}")
    print(f"  Report file: {results['report_file']}")
    
    # Verify files were created
    print("\nVerifying generated files...")
    assert results['events_discovered'] > 0
    assert results['events_recommended'] > 0
    # Proposals and scripts might be 0 if no events matched criteria for them
    assert os.path.exists(results['report_file'])
    
    print("\nComplete workflow test finished successfully!")
    return True

if __name__ == "__main__":
    try:
        test_forum_finder_agent_workflow()
    except Exception as e:
        print(f"\nError during Forum Finder Agent testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)