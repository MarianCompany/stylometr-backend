from db.session import SessionLocal
from db.seed.roles import seed_roles

def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()