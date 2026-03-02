 
CIS4517 Research and Development Project 
 
Project proposal 
1. Your Name 	Kelvin Oteri 	2. 	Course 	title: 	 	Research 	and 
Development Project 
 
3. Email  
 	26339188@edgehill.ac.uk 
4. Module code and name 	CIS4517 Research and Development Project 
 
5. Names of potential project supervisors 
(up to three in the descending order of preference)  	Dr Husnain Rafiq 
6. Title or topic area and main research question of your proposed study 
Proposed Title 
Design and Development of an AI-Assisted Adaptive Software System for Dynamic Visual Content in Domestic Display Frames 
 
Topic Area 
Adaptive software systems; artificial intelligence integration; ambient and domestic computing; intelligent user interfaces. 
 
Main Research Question 
How can existing AI services be effectively integrated into a software system to enable adaptive and contextaware visual content for domestic display frames? 
 
 
7. What are the aim and objectives of your study? 
Aim 
•	The aim of this project is to design, implement, and evaluate a software-based prototype that uses existing AI services to dynamically adapt visual content for domestic display frames based on contextual and user-driven factors. 
 
Objectives 
•	To critically review existing research on adaptive systems, ambient displays, and AI-assisted personalisation in domestic contexts 
•	To design a modular software architecture capable of supporting dynamic image selection and adaptation. 
•	To integrate third-party AI services into the system to support contextual interpretation and content decision-making without training custom models 
•	To implement a functional Python-based prototype that demonstrates adaptive visual behaviour under different contextual scenarios 
•	To evaluate the prototype through scenario-based testing, assessing adaptability, usability, and perceived value compared to static image displays. 
 

Project proposal 
8. Focused review of relevant literature, public datasets and open source packages and rationale for study (at the end of this section, list 8-10 key references) 
Context-aware and adaptive system design is a mature area, but recent work has shifted from “smart environments” as a monolith towards modular architectures that separate context management, reasoning, and adaptation. A 2024 survey of pervasive computing for ambient intelligence highlights that contemporary systems increasingly combine context awareness with data-driven methods, while flagging persistent challenges around privacy, trust, and usable interfaces (Bimpas et al., 2024). In parallel, applied frameworks such as CONTESS show how “context management” can be engineered as a distinct software component (acquisition, modelling, reasoning) feeding downstream decisions (Abdelkarim Ben Sada et al., 2023). 
Research on always-on and domestic displays provides evidence that persistent household displays are meaningful but also socially sensitive: they sit in shared spaces, must be glanceable, and can create unintended exposure of personal information. Recent work on always-on in-home displays (e.g., technology probes used in households) shows how such displays become part of daily routines and how engagement changes over time, which is directly relevant when evaluating whether “dynamic” behaviour is experienced as useful rather than distracting (Menon and Zapico, 2025). 
A useful adjacent lens is context-aware recommendation, because image selection for a frame can be modelled as a recommender problem constrained by time, setting, and user preference. Recent surveys of context-aware recommender systems emphasise that context improves relevance but introduces design complexity: context must be represented, updated, and justified to users (Casillo et al., 2021). However, introducing context increases system complexity: designers must determine which contextual signals are meaningful, how to represent them consistently, and how to combine them with item metadata in a stable selection process. 
That need for control is reinforced by current human-centred AI literature. A 2025 systematic review argues that human-centred AI is best understood through recurring design elements such as user agency, value alignment, and accountability rather than purely technical performance (Schmager, Pappas and Vassilakopoulou, 2025). Design guidance for transparency in human–AI collaboration also shows that providing “reasoning information” can increase trust, while poorly handled uncertainty information can reduce trust—relevant for how the frame explains (or allows users to configure) why certain images are selected (Vössing et al., 2022). For proactive/adaptive systems specifically, recent best-practice work highlights that evaluation should consider not only correctness but also timing, intrusiveness, and user experience over time (Kraus et al., 2025). These ideas shape both system requirements (e.g., manual overrides, sensitivity filters) and evaluation (scenario-based testing plus perceived usefulness and comfort). 
In parallel, advances in large-scale image datasets such as MS COCO (Lin et al., 2015) and Open Images (Kuznetsova et al., 2020) have standardised approaches to image annotation and semantic labelling. These datasets underpin many commercial and academic computer vision systems and illustrate the reliability of metadata-driven image interpretation. The widespread availability of robust vision APIs reflects the maturity of this technological layer. 
 
References:  
ABDELKARIM BEN SADA, NAOURI, A., AMAR KHELLOUFI, SAHRAOUI DHELIM, and NING, H., 2023. A Context-Aware Edge Computing Framework for Smart Internet of Things. Future Internet [online]. 15 (5), pp. 154–154. Available from: https://www.mdpi.com/1999-5903/15/5/154? 
[Accessed 24 Jan 2026]. 
 
BIMPAS, A., VIOLOS, J., LEIVADEAS, A., and VARLAMIS, I., 2024. Leveraging pervasive computing for 
ambient intelligence: A survey on recent advancements, applications and open challenges. 

Project proposal 
Computer Networks [online]. 239, p. 110156. Available from: 
https://www.sciencedirect.com/science/article/pii/S1389128623006011 [Accessed 2 Feb 2026]. 
 
CASILLO, M., COLACE, F., CONTE, D., LOMBARDI, M., SANTANIELLO, D., and VALENTINO, C., 2021. Context-aware recommender systems and cultural heritage: a survey. Journal of Ambient Intelligence and Humanized Computing [online]. Available from: 
https://link.springer.com/article/10.1007/s12652-021-03438-9 [Accessed 7 Feb 2026]. 
 
KRAUS, M., ZEPF, S., WESTHÄUSSER, R., FEUSTEL, I., NIMA ZARGHAM, ASLAN, I., EDWARDS, J., MAYER, S., DIMOSTHENIS KONTOGIORGOS, WAGNER, N., and ANDRÉ, E., 2025. BEHAVE 
AI: BEst Practices and Guidelines for Human-Centric Design and EvAluation of ProactiVE AI Agents. Research Portal (King’s College London) [online]. pp. 175–178. Available from: 
https://dl.acm.org/doi/10.1145/3708557.3716155 [Accessed 7 Feb 2026]. 
 
KUZNETSOVA, A., ROM, H., ALLDRIN, N., UIJLINGS, J., KRASIN, I., PONT-TUSET, J., KAMALI, S., POPOV, S., MALLOCI, M., KOLESNIKOV, A., DUERIG, T., and FERRARI, V., 2020. The Open Images Dataset V4. International Journal of Computer Vision [online]. Available from: 
https://arxiv.org/abs/1811.00982 [Accessed 23 Jan 2026]. 
 
LIN, T.-Y., MAIRE, M., BELONGIE, S., HAYS, J., PERONA, P., RAMANAN, D., DOLLÁR, P., ZITNICK, C., and CORNELL, 2015. Microsoft COCO: Common Objects in Context [online]. Available from: 
https://www.microsoft.com/en-us/research/wp-content/uploads/2014/09/LinECCV14coco.pdf [Accessed 4 Feb 2026]. 
 
MENON, A.R. and ZAPICO, J.L., 2025. Ambient Awareness: Experiencing Always-On Displays in the Life 
of PV Households. DIS ’25: Proceedings of the 2025 ACM Designing Interactive Systems Conference [online]. pp. 789–805. Available from: 
https://dl.acm.org/doi/10.1145/3715336.3735692? [Accessed 5 Feb 2026]. 
 
SCHMAGER, S., PAPPAS, I.O., and VASSILAKOPOULOU, P., 2025. Understanding Human-Centred AI: 
a review of its defining elements and a research agenda. Behaviour & Information Technology [online]. pp. 1–40. Available from: 
https://www.tandfonline.com/doi/full/10.1080/0144929X.2024.2448719? [Accessed 3 Jan 2026]. 
 
VÖSSING, M., KÜHL, N., LIND, M., and SATZGER, G., 2022. Designing Transparency for Effective Human-AI Collaboration. Information Systems Frontiers [online]. 24. Available from: https://link.springer.com/article/10.1007/s10796-022-10284-3 [Accessed 2 Feb 2026]. 
 
 

Project proposal 
9. Detail study design and methods and justify them if possible 
This project will use a design-and-build methodology, produce a software prototype and evaluating its behaviour against defined scenarios. The work focuses on software integration and adaptive decision logic, using existing AI services (APIs) rather than training bespoke machine learning models. 
 
System design and implementation 
A Python-based prototype will be developed using a modular structure: 
•	Content store and metadata layer: images stored locally with associated metadata (e.g., tags, themes, timestamps, user preferences). Storage will use SQLite or structured JSON depending on complexity. 
•	Context inputs: context will be limited to software-accessible factors such as time/date, userselected modes/themes, and interaction history (e.g., likes/skips). 
•	AI service integration: an external image understanding API will be used to generate or enrich metadata (e.g., labels/tags/captions). API access will be via REST calls from Python. No model training will be conducted. 
•	Selection logic (decision engine): the system will select images using rules and/or weighted scoring that combine context signals and AI-produced metadata (e.g., match “evening/calm” mode to images tagged as indoor/night/soft-toned). 
•	Prototype display: a simple interface (e.g., Streamlit) will simulate a digital frame to demonstrate the adaptive behaviour. 
 
 
Evaluation Strategy 
Evaluation will be conducted through scenario-based testing, comparing system behaviour under different contextual conditions (e.g., time of day, thematic preference, recent interaction history). The system’s adaptive outputs will be compared to a non-adaptive slideshow baseline. 
Evaluation criteria will include: 
•	Consistency and coherence of image selection 
•	Responsiveness to contextual changes 
•	Transparency and user controllability 
•	Perceived usefulness and appropriateness 
 
Figure 1:visual representation of system design and evaluation (Image created with AI) 
 
 

Project proposal 
10. Detail a proposed time schedule for the project, with key dates and the milestones of each phase of the project   
 
The project will run over approximately 12 weeks, structured around the interim submission date (7th March 2025) and final completion within a three-month period. 
 
Phase 1: Research, Planning and Initial Design Weeks 1–4 (Up to Interim Submission – 7 March) Activities: 
•	Finalise research question, aim, and SMART objectives 
•	Complete focused literature review 
•	Define contextual variables and system requirements 
•	Design modular software architecture 
•	Produce detailed project plan and risk assessment Milestone (7 March 2025): 
•	Interim report submitted 
•	Approved system design 
•	Clear implementation roadmap 
 
 
 
 
Phase 2: Core Prototype Development 
Weeks 5–8 
Activities: 
•	Implement image storage and metadata structure 
•	Integrate external AI API for semantic tagging 
•	Develop context interpretation layer (e.g., time, user modes) 
•	Implement rule-based / weighted decision logic 
•	Develop prototype display interface Milestone (End of Week 8): 
•	Functional adaptive prototype 
•	Baseline (static slideshow) version implemented 
 
 
Phase 3: Evaluation and Refinement 
Weeks 9–10 
Activities: 
•	Conduct scenario-based evaluation 
•	Compare adaptive vs baseline behaviour 
•	Refine selection logic 
•	Document evaluation findings Milestone: 
•	Stable final prototype 
•	Evaluation results recorded 
 
 
Phase 4: Final Report Completion 
Weeks 11–12 
Activities: 
•	Complete methodology and implementation chapters 
•	Write evaluation, legal, social and ethical analysis 
•	Conduct critical reflection on outcomes 
•	Final editing and formatting Final Milestone: 
•	Completed artefact and final report submitted 
Project proposal 
 
Figure 2: Project timeline visualisation (Image created with AI) 
 
 
 
 
Risk Control 
To maintain feasibility within the three-month timeframe: 
•	AI will be accessed via existing APIs (no model training). 
•	Hardware integration is excluded. 
•	Evaluation will use scenario-based testing rather than large-scale user trials. 
•	Core adaptive functionality will be prioritised before interface refinement. 
 
 
 
 
