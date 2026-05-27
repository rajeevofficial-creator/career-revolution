            'acceptance': "Thank you for working with me on this. I'm pleased to accept the offer at the agreed terms. I look forward to contributing to the team's success.",
            'decline': "Thank you for the offer and for your time throughout the process. After careful consideration, I've decided to pursue another opportunity that better aligns with my career goals at this time. I wish you and the team the best."
        }
    
    def _save_salary_strategy(self, strategy: Dict[str, Any]):
        """Save salary strategy to file."""
        strategy_file = os.path.join(self.output_path, "strategies", 
                                   f"{strategy['company'].replace(' ', '_').lower()}_salary_strategy.json")
        
        with open(strategy_file, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, indent=2, ensure_ascii=False)
        
        print(f"Salary strategy saved to: {strategy_file}")
    
    def generate_interview_preparation_report(self) -> str:
        """Generate interview preparation report."""
        report = []
        report.append("=" * 80)
        report.append("INTERVIEW PREPARATION AGENT - COMPREHENSIVE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Interview Pipeline
        report.append("INTERVIEW PIPELINE")
        report.append("-" * 40)
        report.append(f"Total Interviews: {len(self.interviews)}")
        
        if self.interviews:
            status_counts = {}
            for interview in self.interviews:
                status = interview.preparation_status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            report.append("\nPreparation Status:")
            for status, count in status_counts.items():
                report.append(f"  {status.replace('_', ' ').title()}: {count}")
            
            # Upcoming interviews
            upcoming = [i for i in self.interviews if i.scheduled_date and i.scheduled_date > datetime.now()]
            if upcoming:
                report.append("\nUpcoming Interviews:")
                for i, interview in enumerate(sorted(upcoming, key=lambda x: x.scheduled_date)[:3], 1):
                    days_until = (interview.scheduled_date - datetime.now()).days
                    report.append(f"{i}. {interview.company} - {interview.job_title}")
                    report.append(f"   Date: {interview.scheduled_date.strftime('%Y-%m-%d')} (in {days_until} days)")
                    report.append(f"   Type: {interview.interview_type.value.replace('_', ' ').title()}")
                    report.append(f"   Preparation: {interview.preparation_status.replace('_', ' ').title()}")
                    report.append("")
        else:
            report.append("No interviews scheduled yet.")
            report.append("")
        
        # Company Research Status
        report.append("COMPANY RESEARCH STATUS")
        report.append("-" * 40)
        report.append(f"Companies Researched: {len(self.company_research)}")
        
        if self.company_research:
            report.append("\nRecent Research:")
            for company, research in list(self.company_research.items())[:3]:
                report.append(f"• {company} ({research.industry})")
                if research.recent_news:
                    report.append(f"  Latest: {research.recent_news[0][:60]}...")
                report.append("")
        else:
            report.append("No company research completed yet.")
            report.append("")
        
        # Preparation Resources
        report.append("PREPARATION RESOURCES")
        report.append("-" * 40)
        
        report.append("Research Checklist:")
        for item in self.preparation_templates['research_checklist'][:5]:
            report.append(f"  • {item}")
        
        report.append("\nInterviewer Preparation:")
        for item in self.preparation_templates['interviewer_prep']:
            report.append(f"  • {item}")
        
        report.append("\nDay-of Checklist:")
        for item in self.preparation_templates['day_of_checklist'][:5]:
            report.append(f"  • {item}")
        
        # Salary Negotiation Guidance
        report.append("\nSALARY NEGOTIATION GUIDANCE")
        report.append("-" * 40)
        
        primary_industry = self.profile.get('industries', {}).get('primary', 'pharma_it')
        industry_key = self._map_industry_to_key(primary_industry.replace('_', ' ').title())
        
        if industry_key in self.salary_data:
            report.append(f"Industry: {primary_industry.replace('_', ' ').title()}")
            report.append("Typical Salary Ranges:")
            for role, ranges in self.salary_data[industry_key].items():
                report.append(f"  {role.replace('_', ' ').title()}: CHF {ranges['min']:,.0f} - {ranges['max']:,.0f}")
        
        report.append("\nNegotiation Tips:")
        tips = [
            "1. Know your market value before negotiating",
            "2. Consider total compensation, not just base salary",
            "3. Practice your negotiation conversation",
            "4. Be prepared to walk away if necessary",
            "5. Get all offers in writing"
        ]
        for tip in tips:
            report.append(f"  {tip}")
        
        report.append("")
        report.append("=" * 80)
        report.append("Next Steps:")
        report.append("1. Complete company research for upcoming interviews")
        report.append("2. Practice STAR method responses for common questions")
        report.append("3. Prepare questions to ask interviewers")
        report.append("4. Review salary negotiation strategies")
        report.append("5. Schedule mock interviews if needed")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_complete_workflow(self) -> Dict[str, Any]:
        """Run complete interview preparation workflow."""
        print("\n" + "=" * 60)
        print("Interview Preparation Agent - Starting Complete Workflow")
        print("=" * 60)
        
        # Step 1: Schedule interviews (simulated)
        print("\n1. Scheduling interviews...")
        interviews = []
        
        # Schedule different types of interviews
        interview_types = [
            (InterviewType.HR, "HR Screening"),
            (InterviewType.TECHNICAL, "Technical Assessment"),
            (InterviewType.EXECUTIVE, "Executive Interview")
        ]
        
        companies = ["Major Pharma Company", "Global Consulting Firm", "Financial Services Leader"]
        
        for i, (int_type, description) in enumerate(interview_types):
            interview = self.schedule_interview(
                company=companies[i],
                job_title=f"IT Leadership Role",
                interview_type=int_type,
                scheduled_date=datetime.now() + timedelta(days=3 + i*2)
            )
            interviews.append(interview)
            print(f"   Scheduled: {interview.company} ({description})")
        
        # Step 2: Research companies
        print("\n2. Researching companies...")
        research_results = []
        for company in companies:
            research = self.research_company(company)
            research_results.append(research)
            print(f"   Researched: {company}")
        
        # Step 3: Prepare interview questions
        print("\n3. Preparing interview questions...")
        questions_by_interview = {}
        for interview in interviews:
            questions = self.prepare_interview_questions(interview.id)
            questions_by_interview[interview.id] = questions
            print(f"   Prepared {len(questions)} questions for {interview.company}")
        
        # Step 4: Generate salary strategies
        print("\n4. Generating salary strategies...")
        salary_strategies = []
        for company in companies[:2]:  # First 2 companies
            strategy = self.generate_salary_strategy(company, "IT Leadership Role")
            salary_strategies.append(strategy)
            print(f"   Generated salary strategy for {company}")
        
        # Step 5: Generate report
        print("\n5. Generating interview preparation report...")
        report = self.generate_interview_preparation_report()
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_path, "analytics", f"interview_prep_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_file}")
        print("\nInterview Preparation Agent workflow completed!")
        
        return {
            'interviews_scheduled': len(interviews),
            'companies_researched': len(research_results),
            'questions_prepared': sum(len(q) for q in questions_by_interview.values()),
            'salary_strategies': len(salary_strategies),
            'report_file': report_file,
            'report_preview': report[:500] + "..." if len(report) > 500 else report
        }


def main():
    """Main function to run the Interview Preparation Agent."""
    print("Career Revolution - Interview Preparation Agent")
    print("=" * 60)
    
    agent = InterviewPreparationAgent()
    
    # Run complete workflow
    results = agent.run_complete_workflow()
    
    print(f"\nResults:")
    print(f"  Interviews scheduled: {results['interviews_scheduled']}")
    print(f"  Companies researched: {results['companies_researched']}")
    print(f"  Questions prepared: {results['questions_prepared']}")
    print(f"  Salary strategies: {results['salary_strategies']}")
    print(f"  Report file: {results['report_file']}")
    
    # Print report preview
    print("\nReport Preview:")
    print("-" * 40)
    print(results['report_preview'])
    
    print("\nInterview Preparation Agent completed successfully!")


if __name__ == "__main__":
    main()