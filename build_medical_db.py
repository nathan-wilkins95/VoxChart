import sqlite3
from pathlib import Path

DB_PATH = "medical_terms.db"


def create_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY,
            term TEXT UNIQUE NOT NULL,
            category TEXT,
            common_misrecognition TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_term ON terms(term)")
    conn.commit()
    conn.close()


def seed_terms():
    terms = [
        ("metformin", "medication", "met four min"),
        ("lisinopril", "medication", "lisin a pril"),
        ("atorvastatin", "medication", "a torva stat in"),
        ("hypertension", "diagnosis", "high tension"),
        ("diabetes mellitus", "diagnosis", "diabetes melitus"),
        ("chronic obstructive pulmonary disease", "diagnosis", "COPD"),
        ("congestive heart failure", "diagnosis", "CHF"),
        ("myocardial infarction", "diagnosis", "MI"),
        ("deep vein thrombosis", "diagnosis", "DVT"),
        ("pulmonary embolism", "diagnosis", "PE"),
        ("acute kidney injury", "diagnosis", "AKI"),
        ("chronic kidney disease", "diagnosis", "CKD"),
        ("tachycardia", "finding", "take a cardia"),
        ("bradycardia", "finding", "brady cardia"),
        ("rales", "finding", "rails"),
        ("wheezing", "finding", "weezing"),
    ]
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT OR IGNORE INTO terms (term,category,common_misrecognition) VALUES (?,?,?)",
        terms,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_db()
    seed_terms()
    print("DB created:", Path(DB_PATH).absolute())
