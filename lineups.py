"""
Lineups for India vs New Zealand (India vs NZ T20I context).
Batting order 1–11 as per the provided lineup image; order determines who faces next after a wicket.
ESPNcricinfo player IDs for Statsguru (T20I = class 3).
"""

# India playing XI (batting order 1–11)
INDIA_LINEUP = [
    ("Sanju Samson", 425943),           # 1, wk
    ("Abhishek Sharma", 1070183),       # 2
    ("Ishan Kishan", 720471),           # 3
    ("Hardik Pandya", 625371),          # 4
    ("Suryakumar Yadav", 446507),       # 5, c
    ("Tilak Varma", 1170265),           # 6
    ("Shivam Dube", 714451),            # 7
    ("Axar Patel", 554691),             # 8
    ("Arshdeep Singh", 1125976),        # 9
    ("Varun Chakravarthy", 1108375),   # 10
    ("Jasprit Bumrah", 625383),         # 11
]

# New Zealand playing XI (batting order 1–11)
NEW_ZEALAND_LINEUP = [
    ("Tim Seifert", 625964),            # 1, wk
    ("Finn Allen", 959759),             # 2
    ("Rachin Ravindra", 959767),        # 3
    ("Glenn Phillips", 823509),         # 4
    ("Mark Chapman", 438563),            # 5
    ("Daryl Mitchell", 381743),         # 6
    ("Mitchell Santner", 502714),       # 7, c
    ("James Neesham", 355269),          # 8
    ("Matt Henry", 506612),             # 9
    ("Lockie Ferguson", 493773),         # 10
    ("Jacob Duffy", 547766),            # 11
]

def get_team_lineups():
    return {"India": INDIA_LINEUP, "New Zealand": NEW_ZEALAND_LINEUP}
