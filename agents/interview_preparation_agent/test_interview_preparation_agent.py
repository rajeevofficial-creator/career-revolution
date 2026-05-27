"""
Test script for Interview Preparation Agent
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Adjust the path to import the agent correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from interview_preparation_agent.interview_preparation_agent import InterviewPreparationAgent, InterviewType, QuestionCategory
sys.path.pop(0)

def test_interview_preparation_agent_workflow():
    """Test the complete workflow of the Interview Preparation Agent."""
    print("Testing Interview Preparation Agent Complete Workflow...")
    print("=" * 60)
    
    # Ensure the shared_data/profile directory exists for profile loading
    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'profile'))
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create a dummy master_profile.json if it doesn't exist for testing
    profile_path = os.path.join(profile_dir, "master_profile.json")
    if not os.path.exists(profile_path):
        dummy_profile_content = {
            "skills": {"detailed": {"technical": ["Java", "Cloud Architecture"], "management": ["IT Strategy"]}},
            "experience": {"max_years": 20},
            "education": {"highest_level": "phd"},
            "industries": {"primary": "digital_transformation"}
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_profile_content, f, indent=2)
        print(f"Created dummy profile data at {profile_path}")

    # Create test output directory
    test_output = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_data', 'interviews_test'))
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize agent with test output
    agent = InterviewPreparationAgent(
        profile_data_path=profile_path,
        output_path=test_output
    )
    
    # Run complete workflow
    print("\nRunning complete interview preparation workflow...")
    results = agent.run_complete_workflow()
    
    print(f"\nWorkflow Results:")
    print(f"  Interviews scheduled: {results['interviews_scheduled']}")
    print(f"  Companies researched: {results['companies_researched']}")
    print(f"  Questions prepared: {results['questions_prepared']}")
    print(f"  Salary strategies: {results['salary_strategies']}")
    print(f"  Report file: {results['report_file']}")
    
    # Verify files were created
    print("\nVerifying generated files...")
    assert results['interviews_scheduled'] > 0
    assert results['companies_researched'] > 0
    assert results['questions_prepared'] > 0
    assert results['salary_strategies'] > 0
    assert os.path.exists(results['report_file'])
    
    print("\nComplete workflow test finished successfully!")
    return True

if __name__ == "__main__":
    try:
        test_interview_preparation_agent_workflow()
    except Exception as e:
        print(f"\nError during Interview Preparation Agent testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)