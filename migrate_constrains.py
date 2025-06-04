# Create migrate_constraints.py in your project root
from app import create_app, db
from sqlalchemy import text

def migrate_constraints():
    app = create_app()
    
    with app.app_context():
        try:
            # Add the description column to the constraint table
            with db.engine.connect() as connection:
                connection.execute(text('ALTER TABLE "constraint" ADD COLUMN description VARCHAR(200) NULL;'))
                connection.commit()
                print("Added description column to constraint table")
            
            print("Constraint migration completed successfully!")
            
        except Exception as e:
            print(f"Migration error: {e}")
            print("Note: If column already exists, this is normal and can be ignored.")

if __name__ == "__main__":
    migrate_constraints()