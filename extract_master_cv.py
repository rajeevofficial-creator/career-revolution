import json
import asyncio
from app.services.llm_analysis import LLMAnalysisService

ocr_text = """
Rajeev Sharma
IT Manager with hands on experience 
in delivering business priorities
EXPERTISE
 Passionate IT Manager focused on leveraging digital technologies to enable 
value-driven partnership between IT and Business. 
delivering business excellence and transformational IT programs.  Defined and consulted on global IT strategies, 
to data insight, post-merger IT integrations, implementation of
(ServiceNow, SAP, Oracle, Salesforce, Magento E
defined Architect for enterprise processes and financial maturity, 
Vendors and Outsourcing contracts.  Entrepreneurial mindset with exposure to multiple Industries (Retail, 
Pharmaceutical, Technology Consultation, Telecom and Automotive)
PROFESSIONAL EXPERIENCE
2025 – 2026 Product Owner & AI Product Architect (Startup)
Startup  Product Vision & Execution: Defined the roadmap, data strategy and 
orchestrated the development of a multi-agent AI system capable of 
autonomous financial reasoning, moving from concept to MVP.
2024 – 2024 Program Manager – PMO Setup and SAP S/4 rollout PMO
MSC Cruises (Infosys Consulting AG)  Analyzed current IT governance setup and proposed an efficient PMO 
setup with application portfolio optimization approach with a 
realization of 15% optimization over next 3 years
 Defined governance frameworks and policies, redefined portfolios, 
Risk trackers, financial dashboards to enable continual improvements
 SAP S/4 Hana ERP PMO for managing other consulting company 
and internal stakeholder for on time delivery of program.
2023 – 2024 Project Manager – Mergers, Divestitures & 
acquisitions approach and PMO approach
Infosys Consulting AG
 Led merger acquisition and divestiture point of view, methodology and 
approach definitions with deliverables and artifacts.  Contributed toward PMO services for the potential clients, detailing 
business review services and approach for PMO setup.
2022 – 2023 Product Owner – Global Supplier Portal
British American Tobacco (Infosys Consulting AG) 
 Strategized Product vision and fitment, Managed product features, 
detailed product backlog, coordinated sprints teams, managed stakeholder 
and multiple vendor landscape, enabled best User experience (UX), 
Leveraged Analytics and AI solution  Key platform leveraged were ServiceNow CRM, Celonis process mining 
along with AI based chat  Supplier Portal CSM https://www.batsupplier.com/csm/ for improving 
partnership with more than 13K Suppliers globally on procurement and 
financial topics. 300K + GBP efficiency per year.
2019 – 2022 Business Development & Product Owner
Rasol Solutions – IT Consulting
 Product Owner for creating basic ERP + CRM + SM web application: Enabling small business and schools to have a 
structured data driven business management.  Mobile &Web enabled curriculum delivery for education institutes during COVID.  Lead generation, developing business plan, negotiate and manage vendors.
2016 – 2019 Head IT Governance– IT Finance management & Control 
Dufry AG (Avolta)  Defined and implemented Global IT budgeting and forecasting process, 
responsible for global budget (Capex &Opex) approval and control  Provided IT services total cost of ownership transparency to management and Service Managers
 Responsible for Capex spending prioritization & alignment with business priorities, ROI approach 
was established along with lifecycle cost of service
 Established transparent Intercompany IT cost distribution improving P&L maturity, Audit readiness 
and business relationship  Enabled Contract lifecycle management, leading to nearly 800K USD saving due to wrong invoicing 
and breach of terms for one of the global contract  Represented IT for financial Audits and all financial and treasury applications scoping and RFP process
2016 – 2019 Head IT Governance – IT Process Maturity 
Dufry AG (Avolta)  Implemented practical and simplified IT governance aligned to industry best practice (ITIL, PMP, CGEIT, COBIT)  Standardized Capex and Opex consumption process, improved transparency, reliability and business effectiveness
... [TRUNCATED] ...
2019 Digital Excellence Diploma/ IMD Lausanne 
2012 MBA/ Copenhagen Business School
1998 Bachelors of Engineering/ Pune University, India 
CERTIFICATION 
ITIL V3 professional – IT Service Management 
CGEIT corporate governance in enterprise IT
PMP professional – International Project Management
SAFe 6.0
"""

async def extract_cv_data():
    llm = LLMAnalysisService()
    # No manual model override, let it handle fallbacks
    # Small sleep just in case
    await asyncio.sleep(2)
    
    print("Analyzing CV data...")
    result = await llm.analyze_text(ocr_text, document_context="Master CV (Complete Professional History)")
    
    with open("master_cv_data.json", "w") as f:
        json.dump(result, f, indent=4)
    print("Data saved to master_cv_data.json")

if __name__ == "__main__":
    asyncio.run(extract_cv_data())
