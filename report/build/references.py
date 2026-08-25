"""
The bibliography, as data, in BCU Harvard.

The build fails if a citation has no entry here, or an entry is never cited.
"""

from __future__ import annotations

from typing import Dict

REFERENCES: Dict[str, Dict[str, str]] = {
    # ---------------------------------------------------------- tool use / agents
    "schick2023": {
        "short": "Schick et al.",
        "year": "2023",
        "entry": "Schick, T., Dwivedi-Yu, J., Dessi, R., Raileanu, R., Lomeli, M., "
                 "Hambro, E., Zettlemoyer, L., Cancedda, N. and Scialom, T. (2023) "
                 "'Toolformer: language models can teach themselves to use tools', "
                 "Advances in Neural Information Processing Systems, 36, "
                 "pp. 68539-68551.",
        "locator": "arXiv:2302.04761",
    },
    "yao2023": {
        "short": "Yao et al.",
        "year": "2023",
        "entry": "Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K. and "
                 "Cao, Y. (2023) 'ReAct: synergizing reasoning and acting in language "
                 "models', in Proceedings of the Eleventh International Conference on "
                 "Learning Representations (ICLR 2023). Kigali, Rwanda, 1-5 May.",
        "locator": "arXiv:2210.03629",
    },
    "shinn2023": {
        "short": "Shinn et al.",
        "year": "2023",
        "entry": "Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K. and Yao, S. "
                 "(2023) 'Reflexion: language agents with verbal reinforcement "
                 "learning', Advances in Neural Information Processing Systems, 36, "
                 "pp. 8634-8652.",
        "locator": "arXiv:2303.11366",
    },
    "wu2023": {
        "short": "Wu et al.",
        "year": "2023",
        "entry": "Wu, Q., Bansal, G., Zhang, J., Wu, Y., Zhang, S., Zhu, E., Li, B., "
                 "Jiang, L., Zhang, X. and Wang, C. (2023) 'AutoGen: enabling "
                 "next-generation LLM applications via multi-agent conversation'.",
        "locator": "arXiv:2308.08155",
    },
    "hong2024": {
        "short": "Hong et al.",
        "year": "2024",
        "entry": "Hong, S., Zhuge, M., Chen, J., Zheng, X., Cheng, Y., Wang, J., "
                 "Zhang, C., Wang, Z., Yau, S.K.S., Lin, Z., Zhou, L., Ran, C., "
                 "Xiao, L., Wu, C. and Schmidhuber, J. (2024) 'MetaGPT: meta "
                 "programming for a multi-agent collaborative framework', in "
                 "Proceedings of the Twelfth International Conference on Learning "
                 "Representations (ICLR 2024). Vienna, Austria, 7-11 May.",
        "locator": "arXiv:2308.00352",
    },
    "zhuge2024": {
        "short": "Zhuge et al.",
        "year": "2024",
        "entry": "Zhuge, M., Wang, W., Kirsch, L., Faccio, F., Khizbullin, D. and "
                 "Schmidhuber, J. (2024) 'GPTSwarm: language agents as optimizable "
                 "graphs', in Proceedings of the 41st International Conference on "
                 "Machine Learning (ICML 2024). Vienna, Austria, 21-27 July.",
        "locator": "arXiv:2402.16823",
    },
    "park2023": {
        "short": "Park et al.",
        "year": "2023",
        "entry": "Park, J.S., O'Brien, J., Cai, C.J., Morris, M.R., Liang, P. and "
                 "Bernstein, M.S. (2023) 'Generative agents: interactive simulacra of "
                 "human behaviour', in Proceedings of the 36th Annual ACM Symposium on "
                 "User Interface Software and Technology (UIST 2023). San Francisco, "
                 "CA, 29 October - 1 November. New York: ACM, pp. 1-22.",
        "locator": "doi:10.1145/3586183.3606763",
    },
    "wang2024": {
        "short": "Wang et al.",
        "year": "2024",
        "entry": "Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., Chen, Z., "
                 "Tang, J., Chen, X., Lin, Y., Zhao, W.X., Wei, Z. and Wen, J. (2024) "
                 "'A survey on large language model based autonomous agents', "
                 "Frontiers of Computer Science, 18(6), 186345.",
        "locator": "doi:10.1007/s11704-024-40231-1",
    },
    "xi2023": {
        "short": "Xi et al.",
        "year": "2023",
        "entry": "Xi, Z., Chen, W., Guo, X., He, W., Ding, Y., Hong, B., Zhang, M., "
                 "Wang, J., Jin, S., Zhou, E. and others (2023) 'The rise and potential "
                 "of large language model based agents: a survey'.",
        "locator": "arXiv:2309.07864",
    },
    "cemri2025": {
        "short": "Cemri et al.",
        "year": "2025",
        "entry": "Cemri, M., Pan, M.Z., Yang, S., Agrawal, L.A., Chopra, B., Tiwari, R., "
                 "Keutzer, K., Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., "
                 "Gonzalez, J.E. and Stoica, I. (2025) 'Why do multi-agent LLM systems "
                 "fail?'.",
        "locator": "arXiv:2503.13657",
    },

    # ------------------------------------------------------------- travel planning
    "xie2024": {
        "short": "Xie et al.",
        "year": "2024",
        "entry": "Xie, J., Zhang, K., Chen, J., Zhu, T., Lou, R., Tian, Y., Xiao, Y. "
                 "and Su, Y. (2024) 'TravelPlanner: a benchmark for real-world planning "
                 "with language agents', in Proceedings of the 41st International "
                 "Conference on Machine Learning (ICML 2024). Vienna, Austria, "
                 "21-27 July, pp. 54590-54613.",
        "locator": "arXiv:2402.01622",
    },
    "hao2024": {
        "short": "Hao et al.",
        "year": "2024",
        "entry": "Hao, Y., Chen, Y., Zhang, Y. and Fan, C. (2024) 'Large language "
                 "models can plan your travels rigorously with formal verification "
                 "tools'.",
        "locator": "arXiv:2404.11891",
    },
    "gundawar2024": {
        "short": "Gundawar et al.",
        "year": "2024",
        "entry": "Gundawar, A., Verma, M., Guan, L., Valmeekam, K., Bhambri, S. and "
                 "Kambhampati, S. (2024) 'Robust planning with LLM-Modulo framework: "
                 "case study in trip planning'.",
        "locator": "arXiv:2405.20625",
    },
    "lim2019": {
        "short": "Lim et al.",
        "year": "2019",
        "entry": "Lim, K.H., Chan, J., Leckie, C. and Karunasekera, S. (2019) "
                 "'Tour recommendation and trip planning using location-based social "
                 "media: a survey', Knowledge and Information Systems, 60(3), "
                 "pp. 1247-1275.",
        "locator": "doi:10.1007/s10115-018-1297-4",
    },

    # ------------------------------------------------------------------- protocols
    "anthropic2024": {
        "short": "Anthropic",
        "year": "2024",
        "entry": "Anthropic (2024) Model Context Protocol specification.",
        "locator": "https://modelcontextprotocol.io/specification "
                   "(Accessed: 12 August 2026)",
    },
    "fipa2002": {
        "short": "FIPA",
        "year": "2002",
        "entry": "Foundation for Intelligent Physical Agents (2002) FIPA "
                 "Communicative Act Library specification, SC00037J. Geneva: FIPA.",
        "locator": "http://www.fipa.org/specs/fipa00037/SC00037J.html "
                   "(Accessed: 12 August 2026)",
    },
    "hou2025": {
        "short": "Hou et al.",
        "year": "2025",
        "entry": "Hou, X., Zhao, Y., Wang, S. and Wang, H. (2025) 'Model Context "
                 "Protocol (MCP): landscape, security threats, and future research "
                 "directions'.",
        "locator": "arXiv:2503.23278",
    },
    "crewai2024": {
        "short": "CrewAI",
        "year": "2024",
        "entry": "CrewAI (2024) CrewAI documentation: agents, tasks, crews and tools.",
        "locator": "https://docs.crewai.com (Accessed: 3 August 2026)",
    },

    # ------------------------------------------------------- method and evaluation
    "hevner2004": {
        "short": "Hevner et al.",
        "year": "2004",
        "entry": "Hevner, A.R., March, S.T., Park, J. and Ram, S. (2004) 'Design "
                 "science in information systems research', MIS Quarterly, 28(1), "
                 "pp. 75-105.",
        "locator": "doi:10.2307/25148625",
    },
    "peffers2007": {
        "short": "Peffers et al.",
        "year": "2007",
        "entry": "Peffers, K., Tuunanen, T., Rothenberger, M.A. and Chatterjee, S. "
                 "(2007) 'A design science research methodology for information systems "
                 "research', Journal of Management Information Systems, 24(3), "
                 "pp. 45-77.",
        "locator": "doi:10.2753/MIS0742-1222240302",
    },
    "cohen1960": {
        "short": "Cohen",
        "year": "1960",
        "entry": "Cohen, J. (1960) 'A coefficient of agreement for nominal scales', "
                 "Educational and Psychological Measurement, 20(1), pp. 37-46.",
        "locator": "doi:10.1177/001316446002000104",
    },
    "landis1977": {
        "short": "Landis and Koch",
        "year": "1977",
        "entry": "Landis, J.R. and Koch, G.G. (1977) 'The measurement of observer "
                 "agreement for categorical data', Biometrics, 33(1), pp. 159-174.",
        "locator": "doi:10.2307/2529310",
    },
    "runeson2009": {
        "short": "Runeson and Host",
        "year": "2009",
        "entry": "Runeson, P. and Host, M. (2009) 'Guidelines for conducting and "
                 "reporting case study research in software engineering', Empirical "
                 "Software Engineering, 14(2), pp. 131-164.",
        "locator": "doi:10.1007/s10664-008-9102-8",
    },
    "wohlin2012": {
        "short": "Wohlin et al.",
        "year": "2012",
        "entry": "Wohlin, C., Runeson, P., Host, M., Ohlsson, M.C., Regnell, B. and "
                 "Wesslen, A. (2012) Experimentation in software engineering. Berlin: "
                 "Springer.",
        "locator": "doi:10.1007/978-3-642-29044-2",
    },
    "es2024": {
        "short": "Es et al.",
        "year": "2024",
        "entry": "Es, S., James, J., Espinosa-Anke, L. and Schockaert, S. (2024) "
                 "'RAGAS: automated evaluation of retrieval augmented generation', in "
                 "Proceedings of the 18th Conference of the European Chapter of the "
                 "Association for Computational Linguistics: System Demonstrations. "
                 "St Julians, Malta, 17-22 March, pp. 150-158.",
        "locator": "arXiv:2309.15217",
    },
    "min2023": {
        "short": "Min et al.",
        "year": "2023",
        "entry": "Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P.W., "
                 "Iyyer, M., Zettlemoyer, L. and Hajishirzi, H. (2023) 'FActScore: "
                 "fine-grained atomic evaluation of factual precision in long form text "
                 "generation', in Proceedings of the 2023 Conference on Empirical "
                 "Methods in Natural Language Processing. Singapore, 6-10 December, "
                 "pp. 12076-12100.",
        "locator": "arXiv:2305.14251",
    },
    "ji2023": {
        "short": "Ji et al.",
        "year": "2023",
        "entry": "Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., "
                 "Bang, Y.J., Madotto, A. and Fung, P. (2023) 'Survey of hallucination "
                 "in natural language generation', ACM Computing Surveys, 55(12), "
                 "pp. 1-38.",
        "locator": "doi:10.1145/3571730",
    },

    # ------------------------------------------------------- context and economics
    "liu2024": {
        "short": "Liu et al.",
        "year": "2024",
        "entry": "Liu, N.F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., "
                 "Petroni, F. and Liang, P. (2024) 'Lost in the middle: how language "
                 "models use long contexts', Transactions of the Association for "
                 "Computational Linguistics, 12, pp. 157-173.",
        "locator": "doi:10.1162/tacl_a_00638",
    },
    "unwto2024": {
        "short": "UN Tourism",
        "year": "2024",
        "entry": "UN Tourism (2024) World Tourism Barometer, volume 22, issue 1. "
                 "Madrid: World Tourism Organization.",
        "locator": "doi:10.18111/wtobarometereng",
    },

    # -------------------------------------------------------- professional / legal
    "bcs2022": {
        "short": "BCS",
        "year": "2022",
        "entry": "BCS, The Chartered Institute for IT (2022) BCS code of conduct for "
                 "members. Swindon: BCS.",
        "locator": "https://www.bcs.org/membership-and-registrations/become-a-member/"
                   "bcs-code-of-conduct/ (Accessed: 10 August 2026)",
    },
    "euaiact2024": {
        "short": "European Union",
        "year": "2024",
        "entry": "European Union (2024) Regulation (EU) 2024/1689 of the European "
                 "Parliament and of the Council of 13 June 2024 laying down harmonised "
                 "rules on artificial intelligence (Artificial Intelligence Act). "
                 "Official Journal of the European Union, L 1689.",
        "locator": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj "
                   "(Accessed: 10 August 2026)",
    },
    "ico2023": {
        "short": "Information Commissioner's Office",
        "year": "2023",
        "entry": "Information Commissioner's Office (2023) Guidance on AI and data "
                 "protection. Wilmslow: ICO.",
        "locator": "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/"
                   "artificial-intelligence/guidance-on-ai-and-data-protection/ "
                   "(Accessed: 10 August 2026)",
    },
}

