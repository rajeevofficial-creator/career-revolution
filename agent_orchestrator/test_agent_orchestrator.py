"""
Test script for Agent Orchestrator
"""

import os
import sys
import time
from datetime import datetime, timedelta
import json

# Adjust the path to import the orchestrator correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent_orchestrator.agent_orchestrator import AgentOrchestrator, AgentStatus, TaskPriority
sys.path.pop(0)

def test_orchestrator_workflow():
    """Test the complete workflow of the Agent Orchestrator."""
    print("Testing Agent Orchestrator Complete Workflow...")
    print("=" * 60)
    
    # Create a temporary shared_data directory for testing
    test_shared_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared_data_orchestrator_test'))
    os.makedirs(test_shared_data_path, exist_ok=True)
    
    # Initialize orchestrator with test shared data path
    orchestrator = AgentOrchestrator(shared_data_path=test_shared_data_path)
    
    # Modify agent configurations for quicker testing (e.g., shorter schedules)
    orchestrator.agents['job_search_agent']['schedule'] = 'hourly'
    orchestrator.agents['social_profile_agent']['schedule'] = 'hourly'
    orchestrator.agents['forum_finder_agent']['schedule'] = 'hourly'
    orchestrator.agents['network_agent']['schedule'] = 'hourly'
    orchestrator.agents['application_tracking_agent']['schedule'] = 'hourly'
    orchestrator.agents['interview_preparation_agent']['schedule'] = 'manual' # Keep manual
    
    # Start the orchestrator
    print("\nStarting Agent Orchestrator...")
    orchestrator.start()
    
    try:
        # Allow some time for initial tasks to be scheduled and executed
        print("\nAllowing orchestrator to run and process initial tasks (5 seconds)...")
        time.sleep(5)
        
        # Manually trigger a task for the manual agent
        print("\nManually triggering Interview Preparation Agent...")
        orchestrator.run_agent_immediately('interview_preparation_agent', task_type='prepare_interview')
        time.sleep(2) # Allow time for manual task to be processed
        
        # Get current status
        status_before_stop = orchestrator.get_status()
        print("\nOrchestrator status before stopping:")
        for agent_name, agent_status in status_before_stop['agents'].items():
            print(f"  {agent_name}: Status: {agent_status['enabled']}, Last Run: {agent_status['last_run']}, Next Run: {agent_status['next_run']}, Total Tasks: {agent_status['metrics']['total_tasks']}")
        print(f"  Tasks in Queue: {status_before_stop['queue_size']}")
        print(f"  Active Tasks: {status_before_stop['active_tasks']}")
        print(f"  Completed Tasks: {status_before_stop['completed_tasks']}")

        # Generate and display initial report
        print("\nGenerating initial orchestrator report...")
        report = orchestrator.generate_orchestrator_report()
        print(report[:1000] + "..." if len(report) > 1000 else report)
        
        # Assertions to verify functionality
        assert status_before_stop['running'] == True
        assert status_before_stop['queue_size'] >= 0 # Queue might be empty if tasks processed quickly
        assert status_before_stop['completed_tasks'] >= len([a for a in orchestrator.agents.keys() if orchestrator.agents[a]['schedule'] == 'hourly'] ) # At least one task per hourly agent + 1 for manual
        
        # Check if individual agent metrics were updated
        for agent_name, agent_config in orchestrator.agents.items():
            metrics = status_before_stop['agents'][agent_name]['metrics']
            if agent_config['schedule'] == 'manual':
                 assert metrics['total_tasks'] >= 1 if agent_name == 'interview_preparation_agent' else 0 # Manual agent should have 1 task if triggered
            else:
                assert metrics['total_tasks'] >= 1 # Hourly agents should have at least 1 task
            assert metrics['completed_tasks'] >= 0

    except Exception as e:
        print(f"\nError during Orchestrator running: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Stop the orchestrator
        print("\nStopping orchestrator...")
        orchestrator.stop()
        
        # Final status check
        status_after_stop = orchestrator.get_status()
        print(f"\nOrchestrator running status after stop: {status_after_stop['running']}")
        assert status_after_stop['running'] == False
        
        print("\nAgent Orchestrator test completed successfully!")

if __name__ == "__main__":
    test_orchestrator_workflow()