from app import create_app, db
from app.models import User, ShiftDefinition, Worker, Constraint, ScheduledShift

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'ShiftDefinition': ShiftDefinition,
        'Worker': Worker,
        'Constraint': Constraint,
        'ScheduledShift': ScheduledShift
    }

if __name__ == '__main__':
    app.run(debug=True)