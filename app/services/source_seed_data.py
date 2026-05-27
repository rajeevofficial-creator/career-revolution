"""
Curated seed sources per country.

These are hand-verified, high-quality sources that form the reliable foundation
of the job sourcing pipeline. The LLM discovery layer adds on top of these.

Categories:
  standard_portal         — Local job boards (jobs.ch, StepStone.de, Reed.co.uk)
  global_with_local       — Global platforms filtered to the country (LinkedIn, Indeed)
  boutique_recruiter      — Specialist recruitment firms with local presence
  company_career_page     — Direct career pages of major employers
  government_portal       — Official government/public-sector job boards
  professional_network    — Industry association or alumni boards
"""

SEED_SOURCES: dict[str, list[dict]] = {

    # ─────────────────────────────────────────────────────────────────────────
    "Switzerland": [
        # ── Standard local portals ────────────────────────────────────────
        {"name": "Jobs.ch",             "url": "https://www.jobs.ch/en/",                  "source_type": "standard_portal",       "quality_score": 92, "tags": ["Switzerland", "General"]},
        {"name": "Jobscout24.ch",       "url": "https://www.jobscout24.ch/en/",             "source_type": "standard_portal",       "quality_score": 88, "tags": ["Switzerland", "General"]},
        {"name": "Jobup.ch",            "url": "https://www.jobup.ch/en/",                  "source_type": "standard_portal",       "quality_score": 85, "tags": ["Switzerland", "General"]},
        {"name": "Jobwinner.ch",        "url": "https://www.jobwinner.ch/",                 "source_type": "standard_portal",       "quality_score": 80, "tags": ["Switzerland", "General"]},
        {"name": "Monster Switzerland", "url": "https://www.monster.ch/",                   "source_type": "standard_portal",       "quality_score": 78, "tags": ["Switzerland", "General"]},
        {"name": "Jobgate.ch",          "url": "https://www.jobgate.ch/",                   "source_type": "standard_portal",       "quality_score": 72, "tags": ["Switzerland", "General"]},
        {"name": "ITJobs.ch",           "url": "https://www.itjobs.ch/",                    "source_type": "standard_portal",       "quality_score": 80, "tags": ["Switzerland", "IT", "Technology"]},
        {"name": "SwissDev Jobs",       "url": "https://swissdevjobs.ch/",                  "source_type": "standard_portal",       "quality_score": 78, "tags": ["Switzerland", "Technology", "Engineering"]},
        {"name": "Finance Jobs CH",     "url": "https://www.financejobs.ch/",               "source_type": "standard_portal",       "quality_score": 82, "tags": ["Switzerland", "Finance", "Banking"]},
        {"name": "Pharma Jobs CH",      "url": "https://www.pharmajobs.ch/",                "source_type": "standard_portal",       "quality_score": 80, "tags": ["Switzerland", "Pharma", "Life Sciences"]},
        # ── Global with local filter ──────────────────────────────────────
        {"name": "LinkedIn Switzerland","url": "https://www.linkedin.com/jobs/search/?geoId=106693272", "source_type": "global_with_local", "quality_score": 95, "tags": ["Switzerland", "Global", "Professional"]},
        {"name": "Indeed Switzerland",  "url": "https://www.indeed.ch/",                   "source_type": "global_with_local",     "quality_score": 88, "tags": ["Switzerland", "Global"]},
        {"name": "Glassdoor Switzerland","url": "https://www.glassdoor.ch/",               "source_type": "global_with_local",     "quality_score": 82, "tags": ["Switzerland", "Global", "Reviews"]},
        {"name": "XING Jobs Switzerland","url": "https://www.xing.com/jobs/search?sc_o=jobs_topnav_button&location=Switzerland", "source_type": "global_with_local", "quality_score": 78, "tags": ["Switzerland", "DACH", "Professional"]},
        # ── Government / official ─────────────────────────────────────────
        {"name": "Swiss Federal Jobs (admin.ch)", "url": "https://www.stelle.admin.ch/stelle/de/home.html", "source_type": "government_portal", "quality_score": 85, "tags": ["Switzerland", "Government", "Public Sector"]},
        # ── Boutique & specialist recruiters ─────────────────────────────
        {"name": "Swisslinx",           "url": "https://www.swisslinx.com/jobs",            "source_type": "boutique_recruiter",    "quality_score": 90, "tags": ["Switzerland", "Finance", "Banking", "Executive"]},
        {"name": "Rocken AG",           "url": "https://rocken.jobs/",                      "source_type": "boutique_recruiter",    "quality_score": 88, "tags": ["Switzerland", "Technology", "Engineering", "Management"]},
        {"name": "Stamford Consultants","url": "https://www.stamford.ch/jobs",               "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["Switzerland", "Finance", "Banking", "Private Equity"]},
        {"name": "Michael Page Switzerland","url": "https://www.michaelpage.ch/jobs",        "source_type": "boutique_recruiter",    "quality_score": 87, "tags": ["Switzerland", "Executive", "Finance", "Tech"]},
        {"name": "Robert Half Switzerland","url": "https://www.roberthalf.ch/en/jobs",       "source_type": "boutique_recruiter",    "quality_score": 83, "tags": ["Switzerland", "Finance", "Accounting", "Technology"]},
        {"name": "Hays Switzerland",    "url": "https://www.hays.ch/en/job-offers",          "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["Switzerland", "IT", "Engineering", "Finance"]},
        {"name": "Adecco Switzerland",  "url": "https://www.adecco.ch/en/job-search/",       "source_type": "boutique_recruiter",    "quality_score": 80, "tags": ["Switzerland", "General", "Staffing"]},
        {"name": "Randstad Switzerland","url": "https://www.randstad.ch/jobs/",              "source_type": "boutique_recruiter",    "quality_score": 78, "tags": ["Switzerland", "General", "Staffing"]},
        {"name": "Harvey Nash Switzerland","url": "https://www.harveynash.com/jobs/",        "source_type": "boutique_recruiter",    "quality_score": 80, "tags": ["Switzerland", "IT", "Technology", "Leadership"]},
        {"name": "Experis Switzerland", "url": "https://www.experis.ch/en/jobs",             "source_type": "boutique_recruiter",    "quality_score": 78, "tags": ["Switzerland", "IT", "Engineering"]},
        {"name": "PageGroup Switzerland","url": "https://www.page.ch/jobs",                  "source_type": "boutique_recruiter",    "quality_score": 83, "tags": ["Switzerland", "Executive", "Professional"]},
        {"name": "Spencer Stuart Switzerland","url": "https://www.spencerstuart.com",        "source_type": "boutique_recruiter",    "quality_score": 88, "tags": ["Switzerland", "Executive", "C-Suite", "Board"]},
        {"name": "Kienbaum Switzerland","url": "https://www.kienbaum.com/en/",               "source_type": "boutique_recruiter",    "quality_score": 80, "tags": ["Switzerland", "Executive", "Leadership"]},
        {"name": "Antal International CH","url": "https://www.antal.com/jobs?country=ch",   "source_type": "boutique_recruiter",    "quality_score": 75, "tags": ["Switzerland", "Management", "Finance"]},
        # ── Major employer career pages ───────────────────────────────────
        # URLs point to the actual job-search/listing page (with CH filter where possible),
        # not just the careers homepage. The vetting step will further refine these.
        {"name": "Roche Careers (CH)",       "url": "https://careers.roche.com/global/en/search-results?facetCountry=CH",    "source_type": "company_career_page",   "quality_score": 92, "tags": ["Switzerland", "Pharma", "Life Sciences", "Basel"]},
        {"name": "Novartis Careers (CH)",    "url": "https://www.novartis.com/careers/search-jobs?country=Switzerland",      "source_type": "company_career_page",   "quality_score": 92, "tags": ["Switzerland", "Pharma", "Life Sciences", "Basel"]},
        {"name": "Nestlé Careers (CH)",      "url": "https://www.nestle.com/jobs/search-jobs?country=Switzerland",           "source_type": "company_career_page",   "quality_score": 88, "tags": ["Switzerland", "FMCG", "Vevey"]},
        {"name": "UBS Careers (CH)",         "url": "https://www.ubs.com/global/en/careers/job-search.html",                 "source_type": "company_career_page",   "quality_score": 90, "tags": ["Switzerland", "Banking", "Finance", "Zurich"]},
        {"name": "ABB Careers (CH)",         "url": "https://careers.abb/global/en/search-results?facetCountry=CH",          "source_type": "company_career_page",   "quality_score": 88, "tags": ["Switzerland", "Engineering", "Technology", "Automation"]},
        {"name": "Swiss Re Careers",         "url": "https://www.swissre.com/careers/job-opportunities.html",                "source_type": "company_career_page",   "quality_score": 87, "tags": ["Switzerland", "Insurance", "Finance", "Zurich"]},
        {"name": "Zurich Insurance Careers (CH)","url": "https://www.zurich.com/en/careers/search-for-jobs?country=Switzerland", "source_type": "company_career_page", "quality_score": 87, "tags": ["Switzerland", "Insurance", "Finance", "Zurich"]},
        {"name": "Lonza Careers (CH)",       "url": "https://careers.lonza.com/jobs?country=Switzerland",                    "source_type": "company_career_page",   "quality_score": 85, "tags": ["Switzerland", "Pharma", "Life Sciences", "Basel"]},
        {"name": "Syngenta Careers (CH)",    "url": "https://www.syngenta.com/en/careers/jobs?country=Switzerland",          "source_type": "company_career_page",   "quality_score": 83, "tags": ["Switzerland", "Agri", "Life Sciences", "Basel"]},
        {"name": "Givaudan Careers",         "url": "https://careers.givaudan.com/",                                         "source_type": "company_career_page",   "quality_score": 83, "tags": ["Switzerland", "Specialty Chemicals", "Zurich"]},
        {"name": "Schindler Careers (CH)",   "url": "https://www.schindler.com/com/internet/en/careers/jobs.html",            "source_type": "company_career_page",   "quality_score": 80, "tags": ["Switzerland", "Engineering", "Elevator", "Ebikon"]},
        {"name": "Barry Callebaut Careers",  "url": "https://www.barry-callebaut.com/en/group/careers/job-opportunities",    "source_type": "company_career_page",   "quality_score": 78, "tags": ["Switzerland", "FMCG", "Zurich"]},
        {"name": "Julius Baer Careers",      "url": "https://www.juliusbaer.com/en/careers/job-openings/",                   "source_type": "company_career_page",   "quality_score": 85, "tags": ["Switzerland", "Banking", "Finance", "Wealth Management", "Zurich"]},
        {"name": "Swiss Post Careers",       "url": "https://www.post.ch/en/about-us/jobs-and-careers/job-search",           "source_type": "company_career_page",   "quality_score": 78, "tags": ["Switzerland", "Logistics", "Public"]},
        {"name": "SBB Careers",              "url": "https://company.sbb.ch/en/working-for-sbb/vacancies.html",              "source_type": "company_career_page",   "quality_score": 78, "tags": ["Switzerland", "Transport", "Public", "Engineering"]},
        {"name": "Swisscom Careers",         "url": "https://www.swisscom.ch/en/about/jobs/open-positions.html",             "source_type": "company_career_page",   "quality_score": 82, "tags": ["Switzerland", "Telecom", "Technology"]},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    "Germany": [
        {"name": "StepStone.de",        "url": "https://www.stepstone.de/",                 "source_type": "standard_portal",       "quality_score": 93, "tags": ["Germany", "General"]},
        {"name": "XING Jobs Germany",   "url": "https://www.xing.com/jobs",                 "source_type": "standard_portal",       "quality_score": 88, "tags": ["Germany", "DACH", "Professional"]},
        {"name": "Jobware.de",          "url": "https://www.jobware.de/",                   "source_type": "standard_portal",       "quality_score": 82, "tags": ["Germany", "General"]},
        {"name": "Karriere.de",         "url": "https://www.karriere.de/",                  "source_type": "standard_portal",       "quality_score": 80, "tags": ["Germany", "General"]},
        {"name": "LinkedIn Germany",    "url": "https://www.linkedin.com/jobs/search/?geoId=101282230", "source_type": "global_with_local", "quality_score": 95, "tags": ["Germany", "Global", "Professional"]},
        {"name": "Indeed Germany",      "url": "https://de.indeed.com/",                    "source_type": "global_with_local",     "quality_score": 87, "tags": ["Germany", "Global"]},
        {"name": "Bundesagentur für Arbeit","url": "https://www.arbeitsagentur.de/jobsuche/","source_type": "government_portal",    "quality_score": 85, "tags": ["Germany", "Government", "Official"]},
        {"name": "Michael Page Germany","url": "https://www.michaelpage.de/jobs",           "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["Germany", "Executive", "Finance", "Tech"]},
        {"name": "Hays Germany",        "url": "https://www.hays.de/stellenangebote",        "source_type": "boutique_recruiter",    "quality_score": 84, "tags": ["Germany", "IT", "Engineering", "Finance"]},
        {"name": "Robert Walters Germany","url": "https://www.robertwalters.de/jobs.html",  "source_type": "boutique_recruiter",    "quality_score": 82, "tags": ["Germany", "Finance", "Legal", "Tech"]},
        {"name": "SAP Careers",         "url": "https://jobs.sap.com/",                     "source_type": "company_career_page",   "quality_score": 92, "tags": ["Germany", "Technology", "ERP", "Walldorf"]},
        {"name": "Siemens Careers",     "url": "https://www.siemens.com/global/en/company/jobs.html", "source_type": "company_career_page", "quality_score": 90, "tags": ["Germany", "Engineering", "Technology"]},
        {"name": "BMW Group Careers",   "url": "https://www.bmwgroup.com/en/company/jobs.html", "source_type": "company_career_page", "quality_score": 88, "tags": ["Germany", "Automotive", "Engineering", "Munich"]},
        {"name": "Deutsche Bank Careers","url": "https://careers.db.com/",                  "source_type": "company_career_page",   "quality_score": 88, "tags": ["Germany", "Banking", "Finance", "Frankfurt"]},
        {"name": "Allianz Careers",     "url": "https://careers.allianz.com/",              "source_type": "company_career_page",   "quality_score": 87, "tags": ["Germany", "Insurance", "Finance", "Munich"]},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    "UK": [
        {"name": "Reed.co.uk",          "url": "https://www.reed.co.uk/",                   "source_type": "standard_portal",       "quality_score": 90, "tags": ["UK", "General"]},
        {"name": "TotalJobs",           "url": "https://www.totaljobs.com/",                "source_type": "standard_portal",       "quality_score": 87, "tags": ["UK", "General"]},
        {"name": "CV-Library",          "url": "https://www.cv-library.co.uk/",             "source_type": "standard_portal",       "quality_score": 84, "tags": ["UK", "General"]},
        {"name": "CityJobs",            "url": "https://www.cityjobs.com/",                  "source_type": "standard_portal",       "quality_score": 80, "tags": ["UK", "Finance", "Banking", "London"]},
        {"name": "Guardian Jobs",       "url": "https://jobs.theguardian.com/",              "source_type": "standard_portal",       "quality_score": 80, "tags": ["UK", "Media", "Public Sector", "Technology"]},
        {"name": "LinkedIn UK",         "url": "https://www.linkedin.com/jobs/search/?geoId=101165590", "source_type": "global_with_local", "quality_score": 95, "tags": ["UK", "Global", "Professional"]},
        {"name": "Indeed UK",           "url": "https://uk.indeed.com/",                    "source_type": "global_with_local",     "quality_score": 88, "tags": ["UK", "Global"]},
        {"name": "Glassdoor UK",        "url": "https://www.glassdoor.co.uk/",              "source_type": "global_with_local",     "quality_score": 82, "tags": ["UK", "Global", "Reviews"]},
        {"name": "GOV.UK Jobs",         "url": "https://www.gov.uk/jobsearch",               "source_type": "government_portal",     "quality_score": 82, "tags": ["UK", "Government", "Civil Service"]},
        {"name": "Michael Page UK",     "url": "https://www.michaelpage.co.uk/jobs",         "source_type": "boutique_recruiter",    "quality_score": 87, "tags": ["UK", "Executive", "Finance", "Tech"]},
        {"name": "Robert Walters UK",   "url": "https://www.robertwalters.co.uk/jobs.html",  "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["UK", "Finance", "Legal", "Tech"]},
        {"name": "Hays UK",             "url": "https://www.hays.co.uk/jobs",                "source_type": "boutique_recruiter",    "quality_score": 84, "tags": ["UK", "IT", "Engineering", "Finance"]},
        {"name": "Harvey Nash UK",      "url": "https://www.harveynash.com/uk/jobs/",        "source_type": "boutique_recruiter",    "quality_score": 82, "tags": ["UK", "IT", "Technology", "Leadership"]},
        {"name": "HSBC Careers",        "url": "https://www.hsbc.com/careers",               "source_type": "company_career_page",   "quality_score": 90, "tags": ["UK", "Banking", "Finance", "London"]},
        {"name": "Barclays Careers",    "url": "https://search.jobs.barclays/",              "source_type": "company_career_page",   "quality_score": 88, "tags": ["UK", "Banking", "Finance", "London"]},
        {"name": "GSK Careers",         "url": "https://jobs.gsk.com/",                      "source_type": "company_career_page",   "quality_score": 87, "tags": ["UK", "Pharma", "Life Sciences"]},
        {"name": "AstraZeneca Careers", "url": "https://careers.astrazeneca.com/",           "source_type": "company_career_page",   "quality_score": 87, "tags": ["UK", "Pharma", "Life Sciences", "Cambridge"]},
        {"name": "Unilever Careers",    "url": "https://careers.unilever.com/",              "source_type": "company_career_page",   "quality_score": 85, "tags": ["UK", "FMCG", "London"]},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    "USA": [
        {"name": "LinkedIn USA",        "url": "https://www.linkedin.com/jobs/",             "source_type": "global_with_local",     "quality_score": 95, "tags": ["USA", "Global", "Professional"]},
        {"name": "Indeed USA",          "url": "https://www.indeed.com/",                   "source_type": "standard_portal",       "quality_score": 92, "tags": ["USA", "General"]},
        {"name": "Glassdoor",           "url": "https://www.glassdoor.com/",                 "source_type": "standard_portal",       "quality_score": 88, "tags": ["USA", "Reviews", "General"]},
        {"name": "ZipRecruiter",        "url": "https://www.ziprecruiter.com/",              "source_type": "standard_portal",       "quality_score": 85, "tags": ["USA", "General"]},
        {"name": "Dice (Tech)",         "url": "https://www.dice.com/",                      "source_type": "standard_portal",       "quality_score": 82, "tags": ["USA", "Technology", "IT"]},
        {"name": "USAJobs (Federal)",   "url": "https://www.usajobs.gov/",                   "source_type": "government_portal",     "quality_score": 85, "tags": ["USA", "Government", "Federal"]},
        {"name": "Robert Half USA",     "url": "https://www.roberthalf.com/jobs",            "source_type": "boutique_recruiter",    "quality_score": 82, "tags": ["USA", "Finance", "Technology", "Staffing"]},
        {"name": "Korn Ferry",          "url": "https://jobs.kornferry.com/",                "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["USA", "Executive", "C-Suite"]},
        {"name": "Spencer Stuart",      "url": "https://www.spencerstuart.com",              "source_type": "boutique_recruiter",    "quality_score": 87, "tags": ["USA", "Executive", "Board", "C-Suite"]},
        {"name": "Amazon Jobs",         "url": "https://www.amazon.jobs/",                  "source_type": "company_career_page",   "quality_score": 90, "tags": ["USA", "Technology", "E-Commerce", "Seattle"]},
        {"name": "Google Careers",      "url": "https://careers.google.com/",               "source_type": "company_career_page",   "quality_score": 90, "tags": ["USA", "Technology", "Mountain View"]},
        {"name": "Microsoft Careers",   "url": "https://careers.microsoft.com/",            "source_type": "company_career_page",   "quality_score": 90, "tags": ["USA", "Technology", "Seattle"]},
        {"name": "Goldman Sachs Careers","url": "https://www.goldmansachs.com/careers/",    "source_type": "company_career_page",   "quality_score": 90, "tags": ["USA", "Banking", "Finance", "New York"]},
        {"name": "JPMorgan Chase Careers","url": "https://careers.jpmorgan.com/",           "source_type": "company_career_page",   "quality_score": 88, "tags": ["USA", "Banking", "Finance", "New York"]},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    "India": [
        {"name": "Naukri.com",          "url": "https://www.naukri.com/",                   "source_type": "standard_portal",       "quality_score": 93, "tags": ["India", "General"]},
        {"name": "LinkedIn India",      "url": "https://www.linkedin.com/jobs/search/?geoId=102713980", "source_type": "global_with_local", "quality_score": 92, "tags": ["India", "Global", "Professional"]},
        {"name": "Shine.com",           "url": "https://www.shine.com/",                    "source_type": "standard_portal",       "quality_score": 82, "tags": ["India", "General"]},
        {"name": "Monster India",       "url": "https://www.monsterindia.com/",              "source_type": "standard_portal",       "quality_score": 80, "tags": ["India", "General"]},
        {"name": "TimesJobs",           "url": "https://www.timesjobs.com/",                "source_type": "standard_portal",       "quality_score": 78, "tags": ["India", "General"]},
        {"name": "Indeed India",        "url": "https://in.indeed.com/",                    "source_type": "global_with_local",     "quality_score": 85, "tags": ["India", "Global"]},
        {"name": "Randstad India",      "url": "https://www.randstad.in/jobs/",              "source_type": "boutique_recruiter",    "quality_score": 78, "tags": ["India", "General", "Staffing"]},
        {"name": "TeamLease Services",  "url": "https://www.teamlease.com/job-listing",     "source_type": "boutique_recruiter",    "quality_score": 76, "tags": ["India", "General", "Staffing"]},
        {"name": "TCS Careers",         "url": "https://www.tcs.com/careers",               "source_type": "company_career_page",   "quality_score": 87, "tags": ["India", "IT", "Technology", "Consulting"]},
        {"name": "Infosys Careers",     "url": "https://www.infosys.com/careers/",          "source_type": "company_career_page",   "quality_score": 87, "tags": ["India", "IT", "Technology", "Consulting"]},
        {"name": "Wipro Careers",       "url": "https://careers.wipro.com/",                "source_type": "company_career_page",   "quality_score": 85, "tags": ["India", "IT", "Technology", "Consulting"]},
        {"name": "HCL Careers",         "url": "https://www.hcltech.com/careers",           "source_type": "company_career_page",   "quality_score": 83, "tags": ["India", "IT", "Technology"]},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    "Singapore": [
        {"name": "MyCareersFuture.sg",  "url": "https://www.mycareersfuture.gov.sg/",       "source_type": "government_portal",     "quality_score": 90, "tags": ["Singapore", "Government", "Official"]},
        {"name": "JobsDB Singapore",    "url": "https://sg.jobsdb.com/",                    "source_type": "standard_portal",       "quality_score": 88, "tags": ["Singapore", "General"]},
        {"name": "JobStreet Singapore", "url": "https://www.jobstreet.com.sg/",             "source_type": "standard_portal",       "quality_score": 85, "tags": ["Singapore", "General"]},
        {"name": "LinkedIn Singapore",  "url": "https://www.linkedin.com/jobs/search/?geoId=102454443", "source_type": "global_with_local", "quality_score": 93, "tags": ["Singapore", "Global", "Professional"]},
        {"name": "Indeed Singapore",    "url": "https://sg.indeed.com/",                    "source_type": "global_with_local",     "quality_score": 85, "tags": ["Singapore", "Global"]},
        {"name": "ST Jobs",             "url": "https://www.straitstimes.com/classifieds/jobs", "source_type": "standard_portal",   "quality_score": 78, "tags": ["Singapore", "General"]},
        {"name": "Michael Page Singapore","url": "https://www.michaelpage.com.sg/jobs",     "source_type": "boutique_recruiter",    "quality_score": 87, "tags": ["Singapore", "Executive", "Finance", "Tech"]},
        {"name": "Hays Singapore",      "url": "https://www.hays.com.sg/job-offers",         "source_type": "boutique_recruiter",    "quality_score": 85, "tags": ["Singapore", "IT", "Finance", "Engineering"]},
        {"name": "Robert Walters SG",   "url": "https://www.robertwalters.com.sg/jobs.html", "source_type": "boutique_recruiter",    "quality_score": 84, "tags": ["Singapore", "Finance", "Legal", "Tech"]},
        {"name": "Randstad Singapore",  "url": "https://www.randstad.com.sg/jobs/",          "source_type": "boutique_recruiter",    "quality_score": 80, "tags": ["Singapore", "General", "Staffing"]},
        {"name": "DBS Bank Careers",    "url": "https://www.dbs.com/careers/",               "source_type": "company_career_page",   "quality_score": 88, "tags": ["Singapore", "Banking", "Finance"]},
        {"name": "OCBC Careers",        "url": "https://www.ocbc.com/group/careers/",        "source_type": "company_career_page",   "quality_score": 85, "tags": ["Singapore", "Banking", "Finance"]},
        {"name": "Singtel Careers",     "url": "https://careers.singtel.com/",               "source_type": "company_career_page",   "quality_score": 83, "tags": ["Singapore", "Telecom", "Technology"]},
        {"name": "Grab Careers",        "url": "https://grab.careers/",                      "source_type": "company_career_page",   "quality_score": 85, "tags": ["Singapore", "Technology", "Fintech", "Startup"]},
    ],
}


def get_seed_sources(country: str) -> list[dict]:
    """Return curated seed sources for the given country, defaulting to Switzerland."""
    return SEED_SOURCES.get(country, SEED_SOURCES.get("Switzerland", []))


def get_supported_countries() -> list[str]:
    return list(SEED_SOURCES.keys())
