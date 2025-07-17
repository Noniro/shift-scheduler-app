# migrate_difficulty_range.py
# Run this script to migrate existing job roles from the old difficulty range to the new 1-5 range

from app import create_app, db
from app.models import JobRole

def migrate_difficulty_range():
    """
    Migrate existing job roles from the old difficulty range (1.0-10.0) to the new range (1-5)
    This maps the old values to the new scale appropriately
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Get all job roles
            job_roles = JobRole.query.all()
            
            if not job_roles:
                print("No job roles found to migrate.")
                return
            
            print(f"Found {len(job_roles)} job roles to migrate...")
            
            for role in job_roles:
                old_difficulty = role.difficulty_multiplier
                
                # Map old range (1.0-10.0) to new range (1-5)
                if old_difficulty <= 1.5:
                    new_difficulty = 1  # Easy/Regular
                elif old_difficulty <= 3.0:
                    new_difficulty = 2  # Light
                elif old_difficulty <= 5.0:
                    new_difficulty = 3  # Moderate
                elif old_difficulty <= 7.5:
                    new_difficulty = 4  # Hard
                else:
                    new_difficulty = 5  # Very Hard
                
                print(f"Migrating '{role.name}': {old_difficulty} -> {new_difficulty}")
                role.difficulty_multiplier = float(new_difficulty)
            
            # Commit all changes
            db.session.commit()
            print(f"Successfully migrated {len(job_roles)} job roles to new difficulty range (1-5)!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration error: {e}")
            print("Rolling back changes...")

if __name__ == "__main__":
    print("Migrating job role difficulty values to new range (1-5)...")
    migrate_difficulty_range()
    print("Migration complete!")