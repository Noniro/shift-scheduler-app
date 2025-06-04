from app import create_app, db
from sqlalchemy import text

def migrate_job_roles():
    app = create_app()
    
    with app.app_context():
        try:
            # Add the new columns to the job_role table
            with db.engine.connect() as connection:
                connection.execute(text("ALTER TABLE job_role ADD COLUMN work_start_time TIME NULL;"))
                connection.commit()
                print("Added work_start_time column")
                
                connection.execute(text("ALTER TABLE job_role ADD COLUMN work_end_time TIME NULL;"))
                connection.commit()
                print("Added work_end_time column")
                
                connection.execute(text("ALTER TABLE job_role ADD COLUMN is_overnight_shift BOOLEAN DEFAULT FALSE NOT NULL;"))
                connection.commit()
                print("Added is_overnight_shift column")
            
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Migration error: {e}")
            print("Note: If columns already exist, this is normal and can be ignored.")

if __name__ == "__main__":
    migrate_job_roles()