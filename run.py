from app import create_app, db
from app.models import User, SchedulingPeriod, JobRole, ShiftDefinition, Worker, Constraint, ScheduledShift # Added JobRole

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'SchedulingPeriod': SchedulingPeriod,
        'JobRole': JobRole, # Added
        'ShiftDefinition': ShiftDefinition,
        'Worker': Worker,
        'Constraint': Constraint,
        'ScheduledShift': ScheduledShift
    }

if __name__ == '__main__':
    app.run(debug=True)