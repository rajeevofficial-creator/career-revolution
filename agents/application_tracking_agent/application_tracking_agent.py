"""
Application Tracking Agent for Career Revolution
Agent for managing and tracking the lifecycle of job applications.
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict, field

class ApplicationStatus(Enum):
    """Status of a job application."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class FollowupType(Enum):
    """Type of follow-up action required."""
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    OTHER = "other"

@dataclass
class Application:
    """Data class representing a job application."""
    id: str
    job_id: str
    job_title: str
    company: str
    status: ApplicationStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    status_updated: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)

class ApplicationTrackingAgent:
    """Agent for tracking and managing job applications."""
    
    def __init__(self, profile_data_path: str = "shared_data/profile/master_profile.json",
                 output_path: str = "shared_data/applications"):
        """Initialize the application tracking agent."""
        self.profile_data_path = profile_data_path
        self.output_path = output_path
        
        # Load profile data
        self.profile = self._load_profile_data()
        
        # Simulated job recommendations (to create applications from)
        self.job_recommendations = [
            {'id': 'job_001', 'title': 'IT Director', 'company': 'Roche'},
            {'id': 'job_002', 'title': 'Digital Transformation Lead', 'company': 'Novartis'},
            {'id': 'job_003', 'title': 'IT Business Partner', 'company': 'UBS'},
            {'id': 'job_004', 'title': 'Senior Project Manager', 'company': 'Zurich Insurance'}
        ]
        
        # Tracking applications
        self.applications = []
        
        # Create output directories
        self._create_output_directories()
    
    def _load_profile_data(self) -> Dict[str, Any]:
        """Load profile data from file."""
        try:
            if os.path.exists(self.profile_data_path):
                with open(self.profile_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _create_output_directories(self):
        """Create necessary output directories."""
        directories = [
            os.path.join(self.output_path, "drafts"),
            os.path.join(self.output_path, "submitted"),
            os.path.join(self.output_path, "analytics")
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def create_application(self, job_data: Dict[str, Any]) -> Application:
        """Create a new application from job data."""
        app_id = f"app_{random.randint(1000, 9999)}_{datetime.now().strftime('%Y%m%d')}"
        application = Application(
            id=app_id,
            job_id=job_data.get('id', 'unknown'),
            job_title=job_data.get('title', 'Unknown Role'),
            company=job_data.get('company', 'Unknown Company'),
            status=ApplicationStatus.DRAFT,
            created_at=datetime.now()
        )
        self.applications.append(application)
        return application
        
    def submit_application(self, application_id: str) -> Application:
        """Move application to submitted status."""
        for app in self.applications:
            if app.id == application_id:
                app.status = ApplicationStatus.SUBMITTED
                app.submitted_at = datetime.now()
                app.status_updated = datetime.now()
                return app
        raise ValueError(f"Application {application_id} not found")

    def update_application_status(self, application_id: str, new_status: ApplicationStatus, note: str = "") -> Application:
        """Update application status and add a note."""
        for app in self.applications:
            if app.id == application_id:
                app.status = new_status
                app.status_updated = datetime.now()
                if note:
                    app.notes.append(f"{datetime.now().strftime('%Y-%m-%d')}: {note}")
                return app
        raise ValueError(f"Application {application_id} not found")

    def get_pending_followups(self) -> List[Application]:
        """Get applications that haven't been updated in a while."""
        pending = []
        now = datetime.now()
        for app in self.applications:
            if app.status == ApplicationStatus.SUBMITTED:
                if app.status_updated and (now - app.status_updated).days > 7:
                    pending.append(app)
        return pending

    def generate_application_report(self) -> str:
        """Generate a summary report of application activities."""
        report = []
        report.append("=" * 80)
        report.append("APPLICATION TRACKING REPORT")
        report.append("=" * 80)
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        status_counts = {}
        for status in ApplicationStatus:
            status_counts[status.value] = len([a for a in self.applications if a.status == status])
            
        report.append("Summary by Status:")
        for status_val, count in status_counts.items():
            report.append(f"  • {status_val.replace('_', ' ').title()}: {count}")
        report.append("")
        
        report.append("Action Recommendations:")
        recommendations = []
        
        # Check for applications in draft
        draft_apps = [app for app in self.applications if app.status == ApplicationStatus.DRAFT]
        if draft_apps:
            recommendations.append(f"1. Complete and submit {len(draft_apps)} draft application(s)")
        
        # Check for applications needing status update
        old_apps = [app for app in self.applications 
                   if app.status == ApplicationStatus.SUBMITTED and 
                   app.status_updated and 
                   (datetime.now() - app.status_updated).days > 14]
        if old_apps:
            recommendations.append(f"2. Follow up on {len(old_apps)} application(s) without updates for 14+ days")
        
        # General recommendations
        if len(self.applications) < 5:
            recommendations.append("3. Increase application volume to improve chances")
        elif len([app for app in self.applications if app.status == ApplicationStatus.INTERVIEW_SCHEDULED]) == 0:
            recommendations.append("3. Focus on improving application quality and targeting")
        else:
            recommendations.append("3. Maintain current application pace and focus on interview preparation")
        
        for rec in recommendations:
            report.append(f"  {rec}")
        
        report.append("")
        report.append("30-Day Goals:")
        report.append("  • Submit 5-10 new applications")
        report.append("  • Achieve 20% interview conversion rate")
        report.append("  • Complete all pending follow-ups")
        report.append("  • Secure at least 2 first-round interviews")
        
        report.append("")
        report.append("=" * 80)
        report.append("Key Metrics:")
        report.append("• Application submission rate")
        report.append("• Interview conversion rate")
        report.append("• Follow-up completion rate")
        report.append("• Time-to-offer (average days)")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_complete_workflow(self) -> Dict[str, Any]:
        """Run complete application tracking workflow."""
        print("\n" + "=" * 60)
        print("Application Tracking Agent - Starting Complete Workflow")
        print("=" * 60)
        
        # Step 1: Create applications from job recommendations
        print("\n1. Creating applications from job recommendations...")
        applications = []
        for job in self.job_recommendations[:3]:  # Create applications for top 3 jobs
            application = self.create_application(job)
            applications.append(application)
            print(f"   Created application: {application.job_title} at {application.company}")
        
        # Step 2: Submit applications
        print("\n2. Submitting applications...")
        submitted = []
        for application in applications[:2]:  # Submit first 2 applications
            submitted_app = self.submit_application(application.id)
            submitted.append(submitted_app)
            print(f"   Submitted: {submitted_app.job_title}")
        
        # Step 3: Simulate status updates
        print("\n3. Simulating application status updates...")
        if submitted:
            # Update first application to under review
            updated = self.update_application_status(
                submitted[0].id, 
                ApplicationStatus.UNDER_REVIEW,
                "Application received and being reviewed"
            )
            print(f"   Status updated: {updated.job_title} → {updated.status.value}")
            
            # Update second application to interview scheduled
            updated2 = self.update_application_status(
                submitted[1].id,
                ApplicationStatus.INTERVIEW_SCHEDULED,
                "First-round interview scheduled for next week"
            )
            print(f"   Status updated: {updated2.job_title} → {updated2.status.value}")
        
        # Step 4: Check pending follow-ups
        print("\n4. Checking pending follow-ups...")
        pending = self.get_pending_followups()
        print(f"   Pending follow-ups: {len(pending)}")
        
        # Step 5: Generate report
        print("\n5. Generating application tracking report...")
        report = self.generate_application_report()
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_path, "analytics", f"application_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_file}")
        print("\nApplication Tracking Agent workflow completed!")
        
        return {
            'applications_created': len(applications),
            'applications_submitted': len(submitted),
            'pending_followups': len(pending),
            'report_file': report_file,
            'report_preview': report[:500] + "..." if len(report) > 500 else report
        }


def main():
    """Main function to run the Application Tracking Agent."""
    print("Career Revolution - Application Tracking Agent")
    print("=" * 60)
    
    agent = ApplicationTrackingAgent()
    
    # Run complete workflow
    results = agent.run_complete_workflow()
    
    print(f"\nResults:")
    print(f"  Applications created: {results['applications_created']}")
    print(f"  Applications submitted: {results['applications_submitted']}")
    print(f"  Pending follow-ups: {results['pending_followups']}")
    print(f"  Report file: {results['report_file']}")
    
    # Print report preview
    print("\nReport Preview:")
    print("-" * 40)
    print(results['report_preview'])
    
    print("\nApplication Tracking Agent completed successfully!")


if __name__ == "__main__":
    main()