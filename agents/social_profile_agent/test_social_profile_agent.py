"""
Test script for Social Profile Agent
"""

import os
import sys
from datetime import datetime, timedelta

# Adjust the path to import the agent correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from social_profile_agent.social_profile_agent import SocialProfileAgent, ContentType, ContentStatus
sys.path.pop(0)

def test_social_profile_agent_workflow():
    """Test the complete workflow of the Social Profile Agent."""
    print("Testing Social Profile Agent Complete Workflow...")
    print("=" * 60)
    
    # Ensure the shared_data/profile directory exists for profile loading
    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'profile'))
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create a dummy master_profile.json if it doesn't exist for testing
    profile_path = os.path.join(profile_dir, "master_profile.json")
    if not os.path.exists(profile_path):
        dummy_profile_content = {
            "skills": {"detailed": {"technical": ["Python", "AI", "Cloud"], "management": ["Leadership"]}},
            "experience": {"max_years": 15},
            "industries": {"primary": "digital_transformation"}
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_profile_content, f, indent=2)
        print(f"Created dummy profile data at {profile_path}")

    # Create test output directory
    test_output = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'content_test'))
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize agent with test output
    agent = SocialProfileAgent(
        profile_data_path=profile_path,
        output_path=test_output
    )
    
    # Run complete workflow
    print("\nRunning complete content creation workflow...")
    results = agent.run_complete_workflow()
    
    print(f"\nWorkflow Results:")
    print(f"  Ideas generated: {results['ideas_generated']}")
    print(f"  Drafts created: {results['drafts_created']}")
    print(f"  Content approved: {results['content_approved']}")
    print(f"  Content scheduled: {results['content_scheduled']}")
    print(f"  Report file: {results['report_file']}")
    
    # Verify files were created
    print("\nVerifying generated files...")
    assert results['ideas_generated'] > 0
    assert results['drafts_created'] > 0
    assert results['content_approved'] > 0
    assert results['content_scheduled'] > 0
    assert os.path.exists(results['report_file'])
    
    print("\nComplete workflow test finished successfully!")
    return True

if __name__ == "__main__":
    try:
        test_social_profile_agent_workflow()
    except Exception as e:
        print(f"\nError during Social Profile Agent testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)