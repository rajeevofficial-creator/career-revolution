"""
Test script for Application Tracking Agent
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Adjust the path to import the agent correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from application_tracking_agent.application_tracking_agent import ApplicationTrackingAgent, ApplicationStatus, FollowupType
sys.path.pop(0)

def test_application_tracking_agent_workflow():
    """Test the complete workflow of the Application Tracking Agent."""
    print("Testing Application Tracking Agent Complete Workflow...")
    print("=" * 60)
    
    # Ensure the shared_data/profile directory exists for profile loading
    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'profile'))
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create a dummy master_profile.json if it doesn't exist for testing
    profile_path = os.path.join(profile_dir, "master_profile.json")
    if not os.path.exists(profile_path):
        dummy_profile_content = {
            "skills": {"detailed": {"technical": ["Python", "SQL"], "management": ["Project Management"]}},
            "experience": {"max_years": 10},
            "education": {"highest_level": "master"},
            "summary": {"total_skills_identified": 5}
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_profile_content, f, indent=2)
        print(f"Created dummy profile data at {profile_path}")

    # Create test output directory
    test_output = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'applications_test'))
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize agent with test output
    agent = ApplicationTrackingAgent(
        profile_data_path=profile_path,
        output_path=test_output
    )
    
    # Run complete workflow
    print("\nRunning complete application tracking workflow...")
    results = agent.run_complete_workflow()
    
    print(f"\nWorkflow Results:")
    print(f"  Applications created: {results['applications_created']}")
    print(f"  Applications submitted: {results['applications_submitted']}")
    print(f"  Pending follow-ups: {results['pending_followups']}")
    print(f"  Report file: {results['report_file']}")
    
    # Verify files were created
    print("\nVerifying generated files...")
    assert results['applications_created'] > 0
    assert results['applications_submitted'] > 0
    assert os.path.exists(results['report_file'])
    
    print("\nComplete workflow test finished successfully!")
    return True

if __name__ == "__main__":
    try:
        test_application_tracking_agent_workflow()
    except Exception as e:
        print(f"\nError during Application Tracking Agent testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)