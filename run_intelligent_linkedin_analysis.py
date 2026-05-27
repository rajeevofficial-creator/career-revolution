"""
RUN INTELLIGENT LINKEDIN ANALYSIS
Main script to run LinkedIn analysis with CV data extraction.
"""

import json
from pathlib import Path
from datetime import datetime

def load_sample_cv_data():
    """Load sample CV data for testing."""
    
    # In production, this would load from the Career Revolution repository
    sample_data = {
        "personal_info": {
            "name": "Rajeev Sharma",
            "email": "rajeev.sharma@mail.ch",
            "phone": "+41 XX XXX XX XX",
            "linkedin": "linkedin.com/in/rajeevsharma",
            "location": "Basel, Switzerland"
        },
        "skills": [
            "Project Management",
            "IT Governance",
            "ServiceNow",
            "Stakeholder Management",
            "Strategic Planning",
            "Agile Methodology",
            "Scrum",
            "Budget Management",
            "Team Leadership",
            "Risk Management",
            "Digital Transformation",
            "Business Analysis",
            "Process Improvement",
            "Vendor Management",
            "Change Management",
            "German Language (B2)",
            "English Language (Fluent)",
            "Hindi Language (Native)"
        ],
        "experiences": [
            {
                "company": "Infosys Consulting",
                "role": "Senior Project Manager",
                "duration": "2018-2024",
                "achievements": [
                    "Led digital transformation projects for pharmaceutical clients",
                    "Managed budgets exceeding €2M",
                    "Directed teams of 15+ consultants",
                    "Improved operational efficiency by 30%"
                ]
            },
            {
                "company": "Previous Employer",
                "role": "Project Manager",
                "duration": "2015-2018",
                "achievements": [
                    "Implemented IT governance frameworks",
                    "Managed vendor relationships",
                    "Improved process efficiency"
                ]
            }
        ],
        "certifications": ["PMP", "CGEIT", "ITIL Foundation", "German B2"],
        "education": ["MBA (IT Management)", "Bachelor of Engineering (Computer Science)"]
    }
    
    return sample_data

def main():
    """Run intelligent LinkedIn analysis."""
    
    print("="*80)
    print("CAREER REVOLUTION - INTELLIGENT LINKEDIN ANALYZER")
    print("="*80)
    print()
    
    # Load CV data (in production, from Career Revolution repository)
    print("📁 LOADING CV DATA FROM CAREER REVOLUTION REPOSITORY...")
    cv_data = load_sample_cv_data()
    
    print(f"✓ Name: {cv_data['personal_info']['name']}")
    print(f"✓ Location: {cv_data['personal_info']['location']}")
    print(f"✓ LinkedIn: {cv_data['personal_info']['linkedin']}")
    print(f"✓ Skills: {len(cv_data['skills'])} extracted")
    print(f"✓ Experiences: {len(cv_data['experiences'])} positions")
    print()
    
    # Import and run the intelligent analyzer
    try:
        # Dynamically import the analyzer classes
        import linkedin_intelligent_analyzer
        import linkedin_intelligent_analyzer_part2
        
        # Create analyzer instance
        analyzer = linkedin_intelligent_analyzer.LinkedInIntelligentAnalyzer(cv_data=cv_data)
        
        # Run analysis
        results = analyzer.analyze_from_cv_data()
        
        print("\n" + "="*80)
        print("✅ INTELLIGENT ANALYSIS COMPLETE!")
        print("="*80)
        
        # Show key findings
        profile_info = results['profile_info']
        current_analysis = results['current_analysis']
        
        print(f"\n📊 KEY FINDINGS FOR {profile_info['name']}:")
        print(f"   • Current Profile Score: {current_analysis['profile_strength']}/100")
        print(f"   • Optimization Priority: {current_analysis['optimization_priority']}")
        print(f"   • Time to Impact: {current_analysis['time_to_impact']}")
        
        print(f"\n🎯 TOP 3 OPTIMIZATION PRIORITIES:")
        weaknesses = current_analysis['weaknesses'][:3]
        for i, weakness in enumerate(weaknesses, 1):
            print(f"   {i}. {weakness}")
        
        print(f"\n🚀 IMMEDIATE ACTIONS:")
        print("   1. Update headline with value proposition")
        print("   2. Rewrite About section with storytelling")
        print("   3. Enhance experience entries with achievements")
        
        print(f"\n📈 EXPECTED OUTCOMES (30 DAYS):")
        print("   • 30% increase in profile visibility")
        print("   • 3%+ engagement rate on posts")
        print("   • 50+ new quality connections")
        
        # Create integration with Career Revolution app
        create_career_revolution_integration(results)
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nRunning fallback analysis...")
        run_fallback_analysis(cv_data)

def create_career_revolution_integration(results):
    """Create integration files for Career Revolution app."""
    
    integration_dir = Path("career_revolution_integration")
    integration_dir.mkdir(exist_ok=True)
    
    # Create JSON file for app integration
    integration_data = {
        "analysis_date": datetime.now().isoformat(),
        "profile_info": results['profile_info'],
        "current_analysis": results['current_analysis'],
        "optimization_strategy": results['optimization_strategy'],
        "app_integration": {
            "dashboard_widget": True,
            "weekly_reminders": True,
            "progress_tracking": True,
            "content_suggestions": True
        }
    }
    
    integration_path = integration_dir / "linkedin_analysis_integration.json"
    with open(integration_path, 'w', encoding='utf-8') as f:
        json.dump(integration_data, f, indent=2, ensure_ascii=False)
    
    # Create HTML widget for Career Revolution dashboard
    html_widget = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        .linkedin-widget {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin: 20px;
        }}
        .widget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .widget-title {{
            font-size: 1.5em;
            font-weight: bold;
        }}
        .profile-score {{
            font-size: 2em;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
        }}
        .progress-bar {{
            height: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: white;
            border-radius: 5px;
        }}
        .task-list {{
            list-style: none;
            padding: 0;
        }}
        .task-item {{
            padding: 10px;
            background: rgba(255,255,255,0.1);
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }}
        .task-checkbox {{
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="linkedin-widget">
        <div class="widget-header">
            <div class="widget-title">LinkedIn Optimization</div>
            <div>Score: {results['current_analysis']['profile_strength']}/100</div>
        </div>
        
        <div class="profile-score">{results['current_analysis']['profile_strength']}/100</div>
        
        <div>This Week's Progress:</div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 25%"></div>
        </div>
        
        <div>This Week's Tasks:</div>
        <ul class="task-list">
            <li class="task-item">
                <input type="checkbox" class="task-checkbox"> Update headline
            </li>
            <li class="task-item">
                <input type="checkbox" class="task-checkbox"> Rewrite About section
            </li>
            <li class="task-item">
                <input type="checkbox" class="task-checkbox"> Enhance experience entries
            </li>
        </ul>
        
        <div style="margin-top: 20px; font-size: 0.9em; opacity: 0.8;">
            Next check-in: Tomorrow at 9:00 AM
        </div>
    </div>
</body>
</html>"""
    
    widget_path = integration_dir / "linkedin_dashboard_widget.html"
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(html_widget)
    
    print(f"\n🔗 CAREER REVOLUTION INTEGRATION:")
    print(f"   • Integration JSON: {integration_path}")
    print(f"   • Dashboard Widget: {widget_path}")
    print(f"   • Reports: linkedin_intelligent_reports/")

def run_fallback_analysis(cv_data):
    """Run fallback analysis if main analyzer fails."""
    
    print("\n" + "="*80)
    print("FALLBACK LINKEDIN ANALYSIS")
    print("="*80)
    
    # Simple analysis based on CV data
    name = cv_data['personal_info']['name']
    linkedin_url = cv_data['personal_info']['linkedin']
    skills = len(cv_data['skills'])
    experiences = len(cv_data['experiences'])
    
    print(f"\n📊 ANALYSIS FOR {name}:")
    print(f"   LinkedIn Profile: {linkedin_url}")
    print(f"   Skills Found: {skills}")
    print(f"   Experience Entries: {experiences}")
    
    print(f"\n🎯 RECOMMENDED OPTIMIZATIONS:")
    print("   1. Update headline to include value proposition")
    print("   2. Rewrite About section with storytelling")
    print("   3. Add achievements to experience entries")
    print("   4. Optimize skills section with keywords")
    print("   5. Start posting content weekly")
    
    # Create simple report
    reports_dir = Path("linkedin_fallback_reports")
    reports_dir.mkdir(exist_ok=True)
    
    report = f"""# LINKEDIN OPTIMIZATION REPORT

## Profile Information
- Name: {name}
- LinkedIn: {linkedin_url}
- Skills: {skills}
- Experiences: {experiences}

## Recommended Actions
1. **Headline Optimization**
   - Change from job title to value proposition
   - Include keywords: Pharma IT, Digital Transformation
   - Add certifications: PMP, CGEIT, ITIL

2. **About Section**
   - Tell your professional story
   - Include quantifiable achievements
   - Add call-to-action for connections

3. **Experience Enhancement**
   - Add achievements to each position
   - Include metrics (€, %, team size)
   - Use action verbs

4. **Content Strategy**
   - Post 3x per week
   - Focus on Pharma IT insights
   - Engage with industry content

## 30-Day Plan
**Week 1:** Profile optimization
**Week 2-4:** Content creation & networking
**Month 2-3:** Thought leadership building

---
Generated by Career Revolution Fallback Analyzer
Date: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    report_path = reports_dir / "fallback_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_path}")

if __name__ == "__main__":
    main()