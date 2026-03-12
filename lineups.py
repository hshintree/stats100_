"""
Lineups for T20I matchups. Batting order 1–11; order determines who faces next after a wicket.
ESPNcricinfo player IDs for Statsguru (T20I = class 3). Use 0 for unknown IDs (default probs used).
"""

# ---------------------------------------------------------------------------
# India vs New Zealand
# ---------------------------------------------------------------------------
INDIA_LINEUP = [
    ("Sanju Samson", 425943),
    ("Abhishek Sharma", 1070183),
    ("Ishan Kishan", 720471),
    ("Hardik Pandya", 625371),
    ("Suryakumar Yadav", 446507),
    ("Tilak Varma", 1170265),
    ("Shivam Dube", 714451),
    ("Axar Patel", 554691),
    ("Arshdeep Singh", 1125976),
    ("Varun Chakravarthy", 1108375),
    ("Jasprit Bumrah", 625383),
]

NEW_ZEALAND_LINEUP = [
    ("Tim Seifert", 625964),
    ("Finn Allen", 959759),
    ("Rachin Ravindra", 959767),
    ("Glenn Phillips", 823509),
    ("Mark Chapman", 438563),
    ("Daryl Mitchell", 381743),
    ("Mitchell Santner", 502714),
    ("James Neesham", 355269),
    ("Matt Henry", 506612),
    ("Lockie Ferguson", 493773),
    ("Jacob Duffy", 547766),
]

# ---------------------------------------------------------------------------
# Argentina vs Suriname  — lineup from match scorecard
# ---------------------------------------------------------------------------
ARGENTINA_LINEUP = [
    ("Pedro Baron", 1203195),
    ("Alejandro Ferguson", 23583),
    ("Lucas Rossi", 1403921),
    ("Alan Kirschbaum", 1193269),
    ("Tomas Rossi", 1287084),
    ("Agustin Rivero", 1193275),
    ("Hernan Fennell", 307184),
    ("Ramiro Escobar", 500055),
    ("Agustin Husain", 414052),
    ("Manuel Iturbe", 1193281),
    ("Juan Cabrera", 1193279),
]

SURINAME_LINEUP = [
    ("Somnath Bharratt", 1526445),
    ("Vejai Hirlal", 917083),   
    ("Vishwar Shaw", 523444),
    ("Khemraj Jaikaran", 870031),
    ("Gavin Singh", 870013),   
    ("Joseph Perry", 1526446),
    ("Xaviee Smith", 1463544),
    ("Troy Dudnath", 345296),
    ("Yuvraj Paul Dayal", 581607),
    ("Arun Gokoel", 345286),
    ("Kishan Singh", 1526448),
]

# ---------------------------------------------------------------------------
# Sri Lanka vs Afghanistan
# ---------------------------------------------------------------------------
SRI_LANKA_LINEUP = [
    ("Pathum Nissanka", 1028655),
    ("Kusal Mendis", 629074),
    ("Kusal Perera", 300631),
    ("Charith Asalanka", 784367),
    ("Dasun Shanaka", 437316),
    ("Kamindu Mendis", 784373),
    ("Wanindu Hasaranga", 784379),
    ("Janith Liyanage", 681681),
    ("Dunith Wellalage", 1152427),
    ("Maheesh Theekshana", 1138316),
    ("Dushmantha Chameera", 552152),
]

AFGHANISTAN_LINEUP = [
    ("Rahmanullah Gurbaz", 974087),
    ("Ibrahim Zadran", 921509),
    ("Rashid Khan", 793463),
    ("Mohammad Nabi", 25913),
    ("Azmatullah Omarzai", 819429),
    ("Gulbadin Naib", 352048),
    ("Fazalhaq Farooqi", 974175),
    ("Naveen ul Haq", 793447),
    ("Noor Ahmad", 1182529),
    ("Mujeeb Ur Rahman", 974109),
    ("Shahidullah Kamal", 0),
]

# ---------------------------------------------------------------------------
# Matchups: (label, team1_name, team2_name, lineup1, lineup2)
# ---------------------------------------------------------------------------
MATCHUPS = [
    ("India vs New Zealand", "India", "New Zealand", INDIA_LINEUP, NEW_ZEALAND_LINEUP),
    ("Argentina vs Suriname", "Argentina", "Suriname", ARGENTINA_LINEUP, SURINAME_LINEUP),
    ("Sri Lanka vs Afghanistan", "Sri Lanka", "Afghanistan", SRI_LANKA_LINEUP, AFGHANISTAN_LINEUP),
]


def get_team_lineups():
    """All teams used in MATCHUPS (for fetching stats)."""
    teams = {}
    for _label, t1, t2, l1, l2 in MATCHUPS:
        if t1 not in teams:
            teams[t1] = l1
        if t2 not in teams:
            teams[t2] = l2
    return teams


def get_matchup(label: str):
    """Return (team1_name, team2_name, lineup1, lineup2) for label."""
    for lbl, t1, t2, l1, l2 in MATCHUPS:
        if lbl == label:
            return (t1, t2, l1, l2)
    return None
