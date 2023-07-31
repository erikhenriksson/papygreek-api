from .config import DEBUG


def is_int(test):
    test = str(test)
    if len(test) != 0 and test[0] == "-":
        test = test[1:]
    return test.isnumeric()


def debug(s):
    if DEBUG:
        print(s)


def cols(table):
    tables = {
        "aow_person": [
            "handwriting",
            "honorific",
            "ethnic",
            "occupation",
            "domicile",
            "age",
            "education",
        ],
        "person": [
            "name",
            "tm_id",
            "gender",
        ],
        "text": [
            "id",
            "series_name",
            "series_type",
            "name",
            "tm",
            "hgv",
            "pleiades",
            "date_not_before",
            "date_not_after",
            "place_name",
            "version",
            "checked",
            "orig_status",
            "reg_status",
            "current",
        ],
        "token": [
            "id",
            "text_id",
            "n",
            "sentence_n",
            "line",
            "line_rend",
            "hand",
            "textpart",
            "aow_n",
            "orig_form",
            "orig_plain",
            "orig_flag",
            "orig_app_type",
            "orig_num",
            "orig_num_rend",
            "orig_lang",
            "orig_info",
            "orig_lemma",
            "orig_postag",
            "orig_relation",
            "orig_head",
            "reg_form",
            "reg_plain",
            "reg_flag",
            "reg_app_type",
            "reg_num",
            "reg_num_rend",
            "reg_lang",
            "reg_info",
            "reg_lemma",
            "reg_postag",
            "reg_relation",
            "reg_head",
            "insertion_id",
            "artificial",
        ],
        "variation": [
            "operation",
            "orig_bef",
            "orig_aft",
            "orig",
            "reg",
            "reg_bef",
            "reg_aft",
            "p_orig_bef",
            "p_orig_aft",
            "p_orig",
            "p_reg",
            "p_reg_bef",
            "p_reg_aft",
        ],
    }
    return tables[table]


def sql_cols(table):
    return ", ".join(cols(table))


def text_types():
    return {
        0: [
            "---",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
            },
        ],
        1: [
            "ADMINISTRATION",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Application",
                    {
                        0: "---",
                        1: "Epikrisis",
                        2: "For tutor/kyrios",
                        3: "Membership",
                        4: "Others",
                        5: "Registration",
                        6: "Seed-Corn",
                        7: "To open testament",
                    },
                ],
                2: [
                    "Appointment",
                    {
                        0: "---",
                        1: "Liturgy",
                        2: "Work",
                    },
                ],
                3: [
                    "Bid",
                    {
                        0: "---",
                        1: "Purchase",
                    },
                ],
                4: [
                    "Cancellation",
                    {
                        0: "---",
                    },
                ],
                5: [
                    "Certificate",
                    {
                        0: "---",
                        1: "Diploma",
                        2: "Libelli",
                        3: "Other",
                        4: "Penthemeros/Five naubion",
                        5: "Performed public work",
                    },
                ],
                6: [
                    "Declaration (apographè)",
                    {
                        0: "---",
                        1: "Anachoresis",
                        2: "Census declaration",
                        3: "Declaration of birth",
                        4: "Declaration of death",
                        5: "Declaration of inundated/overfloaded land",
                        6: "Declaration of livestock/camels",
                        7: "Epikrisis",
                        8: "Property declaration/property returns",
                    },
                ],
                7: [
                    "Letter",
                    {
                        0: "---",
                        1: "Letter of recommendation (official)",
                        2: "Official correspondence",
                    },
                ],
                8: ["List", {0: "---", 1: "Land/house", 2: "Property", 3: "Taxpayers"}],
                9: [
                    "Memorandum (official)",
                    {
                        0: "---",
                    },
                ],
                10: [
                    "Notice",
                    {
                        0: "---",
                    },
                ],
                11: [
                    "Notification",
                    {
                        0: "---",
                    },
                ],
                12: [
                    "Oath",
                    {
                        0: "---",
                        1: "Assumption liturgy/public work",
                    },
                ],
                13: [
                    "Order",
                    {
                        0: "---",
                        1: "Delivery (military supplies)",
                        2: "Entagion",
                        3: "Payment (military)",
                        4: "Summons (order to arrest)",
                    },
                ],
                14: [
                    "Petition",
                    {0: "---", 1: "Enteuxis (to the king/queen)", 2: "Hypomnema"},
                ],
                15: ["Receipt", {0: "---", 1: "Custom duty", 2: "Tax"}],
                16: [
                    "Report",
                    {
                        0: "---",
                        1: "Administrative",
                        2: "Official Diary (hypomnema)",
                    },
                ],
                17: [
                    "Response (official - ypographè)",
                    {
                        0: "---",
                    },
                ],
            },
        ],
        2: [
            "BUSINESS",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Account",
                    {
                        0: "---",
                        1: "Calculation",
                        2: "Goods",
                        3: "Incoming/outgoing money",
                        4: "Taxes",
                        5: "Transport",
                    },
                ],
                2: [
                    "Acknowledgement",
                    {
                        0: "---",
                        1: "Payment",
                    },
                ],
                3: [
                    "Application",
                    {
                        0: "---",
                        1: "Lease/buy",
                    },
                ],
                4: [
                    "Invoice",
                    {
                        0: "---",
                    },
                ],
                5: [
                    "Letter",
                    {
                        0: "---",
                        1: "Business correspondence",
                    },
                ],
                6: [
                    "List",
                    {
                        0: "---",
                        1: "Expenditure",
                        2: "Items",
                        3: "Others",
                        4: "Payment",
                        5: "Wages",
                    },
                ],
                7: [
                    "Offer",
                    {
                        0: "---",
                        1: "Purchase",
                    },
                ],
                8: [
                    "Order",
                    {
                        0: "---",
                        1: "Delivery",
                        2: "Others",
                        3: "Payment",
                        4: "Transfer Credit in Grain",
                    },
                ],
                9: [
                    "Receipt",
                    {
                        0: "---",
                        1: "Items",
                        2: "Money",
                        3: "of delivery",
                        4: "Payment",
                        5: "Rent",
                    },
                ],
                10: [
                    "Register",
                    {
                        0: "---",
                        1: "Contracts",
                    },
                ],
                11: [
                    "Request",
                    {
                        0: "---",
                        1: "Payment",
                        2: "Refund",
                    },
                ],
            },
        ],
        3: [
            "LAW",
            {
                0: [
                    "---",
                    {
                        0: "---",
                        1: "Obligatory",
                    },
                ],
                1: [
                    "Acknowledgement",
                    {
                        0: "---",
                        1: "Exemption/Release",
                        2: "Of debt",
                        3: "Of performed duty",
                        4: "Other",
                    },
                ],
                2: [
                    "Application",
                    {
                        0: "---",
                        1: "Emancipation",
                    },
                ],
                3: [
                    "Appointment",
                    {
                        0: "---",
                        1: "Representative",
                    },
                ],
                4: [
                    "Authorization",
                    {
                        0: "---",
                        1: "Power of attorney",
                    },
                ],
                5: [
                    "Contract",
                    {
                        0: "---",
                        1: "Adoption",
                        2: "Alienation",
                        3: "Alimony",
                        4: "Appointment (of a guardian/kyrios)",
                        5: "Apprenticeship (didaskalikai)",
                        6: "Association",
                        7: "by arbitration",
                        8: "Cession (parachoresis)",
                        9: "Debt",
                        10: "Deed of gift",
                        11: "Deed of surety",
                        12: "Deposit",
                        13: "Disownment (apokêryxis)",
                        14: "Division",
                        15: "Divorce",
                        16: "Donation: donatio mortis causa (meriteia)",
                        17: "Emancipation (Manumissio/Paramone)",
                        18: "Lease",
                        19: "Loan",
                        20: "Marriage",
                        21: "Nurture",
                        23: "Procuration",
                        24: "Promissory note",
                        25: "Purchase",
                        26: "Recruitment",
                        27: "Renunciation",
                        28: "Sale",
                        29: "Sale on delivery/sale on credit",
                        30: "Settlement (Dialysis)",
                        31: "Sublease",
                        32: "Termination of a contract",
                        33: "Transport",
                        34: "Uncertain",
                        35: "Will (diathêkê)",
                        36: "Work",
                    },
                ],
                6: [
                    "Declaration",
                    {
                        0: "---",
                        1: "Prices",
                    },
                ],
                7: [
                    "List (official)",
                    {
                        0: "---",
                        1: "Survey",
                    },
                ],
                8: [
                    "Nomination",
                    {
                        0: "---",
                        1: "Liturgy",
                        2: "to office",
                    },
                ],
                9: ["Register", {0: "---", 1: "Tax"}],
                10: [
                    "Registration",
                    {
                        0: "---",
                        1: "Property",
                    },
                ],
                11: [
                    "Report",
                    {
                        0: "---",
                        1: "Legal proceedings",
                        2: "Medical",
                    },
                ],
                12: ["Request", {0: "---", 1: "Exemption/Release"}],
            },
        ],
        4: [
            "LAW/ADMINISTRATION",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Order (law/administration)",
                    {
                        0: "---",
                        1: "Decree",
                        2: "Edict",
                        3: "Programma - imperial decision",
                    },
                ],
                2: [
                    "Registration",
                    {
                        0: "---",
                        1: "Loan",
                        2: "Private business",
                        3: "Purchase",
                    },
                ],
            },
        ],
        5: [
            "MILITARY",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Diploma",
                    {
                        0: "---",
                    },
                ],
            },
        ],
        6: [
            "PRIVATE",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Letter",
                    {
                        0: "---",
                        1: "Invitation",
                        2: "Letter of condolence",
                        3: "Letter of recommendation (private)",
                        4: "Private correspondence",
                    },
                ],
                2: [
                    "List",
                    {
                        0: "---",
                        1: "Names",
                    },
                ],
                3: [
                    "Memorandum (private)",
                    {
                        0: "---",
                    },
                ],
                4: [
                    "School text",
                    {
                        0: "---",
                    },
                ],
            },
        ],
        7: [
            "RELIGION",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Dedication",
                    {
                        0: "---",
                    },
                ],
                2: [
                    "Mummy label",
                    {
                        0: "---",
                    },
                ],
                3: [
                    "Oracle",
                    {
                        0: "---",
                    },
                ],
                4: [
                    "Dream",
                    {
                        0: "---",
                        1: "List",
                        2: "Description",
                    },
                ],
            },
        ],
        8: [
            "UNCERTAIN",
            {
                0: [
                    "---",
                    {
                        0: "---",
                    },
                ],
                1: [
                    "Mixed",
                    {
                        0: "---",
                    },
                ],
                2: ["Uncertain", {0: "---", 1: "Uncertain"}],
            },
        ],
    }
