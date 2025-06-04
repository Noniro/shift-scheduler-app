from datetime import datetime, time, timedelta
from app import db

# TODO: Understand the app.db session management and how to handle transactions properly, and converting more files (csv, json) to this format


# Association table for Worker <-> JobRole (Many-to-Many)
worker_jobrole_association = db.Table('worker_jobrole_association',
    db.Column('worker_id', db.Integer, db.ForeignKey('worker.id', ondelete="CASCADE"), primary_key=True),
    db.Column('jobrole_id', db.Integer, db.ForeignKey('job_role.id', ondelete="CASCADE"), primary_key=True)
)

class SchedulingPeriod(db.Model):
    __tablename__ = 'scheduling_period'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    period_start_datetime = db.Column(db.DateTime, nullable=False)
    period_end_datetime = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False) # Indicates if this period is currently active
    # job_roles relationship defined via backref from JobRole
    # shift_definitions relationship defined via backref from ShiftDefinition
    def __repr__(self): return f'<SchedulingPeriod {self.name} ({self.id})>'

# class JobRole(db.Model):
#     __tablename__ = 'job_role'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False) # e.g., "Cook", "Servant"
#     number_needed = db.Column(db.Integer, default=1, nullable=False) # Number needed simultaneously
#     shift_duration_days = db.Column(db.Integer, default=0, nullable=False)
#     shift_duration_hours = db.Column(db.Integer, default=0, nullable=False)
#     shift_duration_minutes = db.Column(db.Integer, default=0, nullable=False)
#     scheduling_period_id = db.Column(db.Integer, db.ForeignKey('scheduling_period.id', ondelete="CASCADE"), nullable=False)
#     scheduling_period = db.relationship('SchedulingPeriod', backref=db.backref('job_roles', lazy='dynamic', cascade="all, delete-orphan"))
#     # defined_slots relationship via backref from ShiftDefinition
#     # qualified_workers relationship via backref from Worker through association table

#     def get_duration_timedelta(self):
#         return timedelta(
#             days=self.shift_duration_days, 
#             hours=self.shift_duration_hours, 
#             minutes=self.shift_duration_minutes
#         )
#     def __repr__(self): return f'<JobRole {self.name} (Period: {self.scheduling_period_id}, Needed: {self.number_needed})>'

# Add these fields to your JobRole class in models.py
# Find the JobRole class and add these new fields:

class JobRole(db.Model):
    __tablename__ = 'job_role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g., "Cook", "Servant"
    number_needed = db.Column(db.Integer, default=1, nullable=False) # Number needed simultaneously
    shift_duration_days = db.Column(db.Integer, default=0, nullable=False)
    shift_duration_hours = db.Column(db.Integer, default=0, nullable=False)
    shift_duration_minutes = db.Column(db.Integer, default=0, nullable=False)
    
    # NEW FIELDS FOR TIME CONSTRAINTS
    work_start_time = db.Column(db.Time, nullable=True)  # e.g., 22:00 for night shift
    work_end_time = db.Column(db.Time, nullable=True)    # e.g., 04:00 for night shift
    is_overnight_shift = db.Column(db.Boolean, default=False, nullable=False)  # True if shift crosses midnight
    
    scheduling_period_id = db.Column(db.Integer, db.ForeignKey('scheduling_period.id', ondelete="CASCADE"), nullable=False)
    scheduling_period = db.relationship('SchedulingPeriod', backref=db.backref('job_roles', lazy='dynamic', cascade="all, delete-orphan"))
    # defined_slots relationship via backref from ShiftDefinition
    # qualified_workers relationship via backref from Worker through association table

    def get_duration_timedelta(self):
        return timedelta(
            days=self.shift_duration_days, 
            hours=self.shift_duration_hours, 
            minutes=self.shift_duration_minutes
        )
        
    def has_time_restrictions(self):
        """Check if this job role has specific working hours"""
        return self.work_start_time is not None and self.work_end_time is not None
        
    def get_working_hours_str(self):
        """Get a string representation of working hours"""
        if not self.has_time_restrictions():
            return "All day"
        
        start_str = self.work_start_time.strftime('%H:%M')
        end_str = self.work_end_time.strftime('%H:%M')
        
        if self.is_overnight_shift:
            return f"{start_str} - {end_str} (next day)"
        else:
            return f"{start_str} - {end_str}"
    
    def __repr__(self): 
        return f'<JobRole {self.name} (Period: {self.scheduling_period_id}, Needed: {self.number_needed})>'

class Worker(db.Model):
    __tablename__ = 'worker'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    max_hours_per_week = db.Column(db.Integer, nullable=True) # Interpreted as max for active period by algorithm
    constraints = db.relationship('Constraint', backref='worker', lazy='dynamic', cascade="all, delete-orphan")
    scheduled_shifts = db.relationship('ScheduledShift', backref='worker_assigned', lazy='dynamic', cascade="all, delete-orphan")
    qualified_roles = db.relationship('JobRole', secondary=worker_jobrole_association,
                                      lazy='subquery', # Eagerly loads roles when worker is loaded
                                      backref=db.backref('qualified_workers', lazy='dynamic'))
    def __repr__(self): return f'<Worker {self.name}>'

class ShiftDefinition(db.Model): # Represents a single coverage slot to be filled
    __tablename__ = 'shift_definition'
    id = db.Column(db.Integer, primary_key=True)
    slot_start_datetime = db.Column(db.DateTime, nullable=False)
    slot_end_datetime = db.Column(db.DateTime, nullable=False)
    instance_number = db.Column(db.Integer, nullable=False) # e.g., Cook slot 1 of 2

    scheduling_period_id = db.Column(db.Integer, db.ForeignKey('scheduling_period.id', ondelete="CASCADE"), nullable=False)
    scheduling_period = db.relationship('SchedulingPeriod', backref=db.backref('shift_definitions', lazy='dynamic')) # Removed cascade from here as period deletion cascades to roles, which cascades to definitions
    
    job_role_id = db.Column(db.Integer, db.ForeignKey('job_role.id', ondelete="CASCADE"), nullable=False)
    job_role = db.relationship('JobRole', backref=db.backref('defined_slots', lazy='dynamic', cascade="all, delete-orphan"))
    
    scheduled_assignment = db.relationship('ScheduledShift', backref='defined_slot', uselist=False, cascade="all, delete-orphan")

    @property
    def name(self): # Name now comes from JobRole
        role_name = self.job_role.name if self.job_role else "Orphaned Role"
        return f"{role_name} - Instance {self.instance_number}"

    @property
    def duration_timedelta(self): return self.slot_end_datetime - self.slot_start_datetime
    @property
    def duration_total_seconds(self): return self.duration_timedelta.total_seconds()
    @property
    def duration_hours_minutes_str(self):
        secs = self.duration_total_seconds; days, secs = divmod(secs, 86400); hrs, secs = divmod(secs, 3600); mins, secs = divmod(secs, 60)
        res = [];_ = [res.append(f"{int(v)}{u}") for v, u in [(days, "d"), (hrs, "h"), (mins, "m")] if v]
        return " ".join(res) if res else "0m"
    def __repr__(self): return f'<ShiftDefinition ID:{self.id} {self.name} {self.slot_start_datetime}-{self.slot_end_datetime}>'

class Constraint(db.Model):
    __tablename__ = 'constraint'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id', ondelete="CASCADE"), nullable=False)
    constraint_type = db.Column(db.String(50), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    def __repr__(self): return f'<Constraint {self.worker.name} - {self.constraint_type} from {self.start_datetime} to {self.end_datetime}>'

class ScheduledShift(db.Model):
    __tablename__ = 'scheduled_shift'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id', ondelete="SET NULL"), nullable=True)
    shift_definition_id = db.Column(db.Integer, db.ForeignKey('shift_definition.id', ondelete="CASCADE"), nullable=False, unique=True)
    def __repr__(self):
        slot_info = self.defined_slot.name if self.defined_slot else f"Slot ID {self.shift_definition_id}"
        worker_name = self.worker_assigned.name if self.worker_assigned else "UNASSIGNED"
        return f'<Assignment: {slot_info} for {worker_name}>'

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))