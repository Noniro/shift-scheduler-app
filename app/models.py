from datetime import datetime, time, timedelta
from app import db
from sqlalchemy import event # For custom listeners if needed

class SchedulingPeriod(db.Model):
    __tablename__ = 'scheduling_period'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    period_start_datetime = db.Column(db.DateTime, nullable=False)
    period_end_datetime = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False) # Only one period can be active for defining/generating

    # Relationship to the shift definitions (coverage slots) that belong to this period
    shift_definitions = db.relationship('ShiftDefinition', backref='scheduling_period', lazy='dynamic', cascade="all, delete-orphan")
    # Relationship to shift templates defined for this period
    shift_templates = db.relationship('ShiftTemplate', backref='scheduling_period', lazy='dynamic', cascade="all, delete-orphan")


    def __repr__(self):
        return f'<SchedulingPeriod {self.name} ({self.id})>'

class ShiftTemplate(db.Model): # NEW: Defines the DURATION of a type of shift for a period
    __tablename__ = 'shift_template'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g., "Standard Guard Shift", "Quick Check"
    duration_days = db.Column(db.Integer, default=0, nullable=False)
    duration_hours = db.Column(db.Integer, default=0, nullable=False)
    duration_minutes = db.Column(db.Integer, default=0, nullable=False)
    scheduling_period_id = db.Column(db.Integer, db.ForeignKey('scheduling_period.id'), nullable=False)
    # Add order if multiple templates are used to fill a day sequentially
    # fill_order = db.Column(db.Integer, default=0)

    def get_duration_timedelta(self):
        return timedelta(days=self.duration_days, hours=self.duration_hours, minutes=self.duration_minutes)

    def __repr__(self):
        return f'<ShiftTemplate {self.name} for Period {self.scheduling_period_id} - {self.duration_days}d {self.duration_hours}h {self.duration_minutes}m>'


class ShiftDefinition(db.Model): # Represents a specific generated coverage slot to be filled
    __tablename__ = 'shift_definition'
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(100), nullable=True) # Name might come from the template or be generic
    slot_start_datetime = db.Column(db.DateTime, nullable=False)
    slot_end_datetime = db.Column(db.DateTime, nullable=False)
    scheduling_period_id = db.Column(db.Integer, db.ForeignKey('scheduling_period.id'), nullable=False)
    # Optional: link to the template that generated this slot
    generated_from_template_id = db.Column(db.Integer, db.ForeignKey('shift_template.id'), nullable=True)
    generated_from_template = db.relationship('ShiftTemplate')


    scheduled_assignment = db.relationship('ScheduledShift', backref='defined_slot', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        template_name = f" (from T:{self.generated_from_template.name})" if self.generated_from_template else ""
        return f'<ShiftDefinition {self.id}{template_name}: {self.slot_start_datetime} to {self.slot_end_datetime}>'

    @property
    def duration_timedelta(self):
        return self.slot_end_datetime - self.slot_start_datetime

    @property
    def duration_total_seconds(self):
        return self.duration_timedelta.total_seconds()
    
    @property
    def name(self): # Dynamically get name from template if available
        if self.generated_from_template:
            return self.generated_from_template.name
        return f"Slot {self.id}"


    @property
    def duration_hours_minutes_str(self):
        secs = self.duration_total_seconds
        days, secs = divmod(secs, 86400)
        hrs, secs = divmod(secs, 3600)
        mins, secs = divmod(secs, 60)
        res = []
        if days: res.append(f"{int(days)}d")
        if hrs: res.append(f"{int(hrs)}h")
        if mins: res.append(f"{int(mins)}m")
        return " ".join(res) if res else "0m"

# Worker, Constraint, ScheduledShift, User models remain largely the same as before
# ... (Worker, Constraint, ScheduledShift, User models as provided in the previous full code response) ...
class Worker(db.Model):
    __tablename__ = 'worker' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    max_hours_per_week = db.Column(db.Integer, nullable=True) # Note: current algorithm treats this as total for period

    constraints = db.relationship('Constraint', backref='worker', lazy='dynamic', cascade="all, delete-orphan")
    scheduled_shifts = db.relationship('ScheduledShift', backref='worker_assigned', lazy='dynamic') # Renamed backref slightly

    def __repr__(self):
        return f'<Worker {self.name}>'

class Constraint(db.Model):
    __tablename__ = 'constraint' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    constraint_type = db.Column(db.String(50), nullable=False) # e.g., "UNAVAILABLE_DAY_RANGE"
    start_datetime = db.Column(db.DateTime, nullable=False) # Start of first unavailable day (00:00:00)
    end_datetime = db.Column(db.DateTime, nullable=False)   # End of last unavailable day (23:59:59)

    def __repr__(self):
        return f'<Constraint {self.worker.name} - {self.constraint_type} from {self.start_datetime} to {self.end_datetime}>'

class ScheduledShift(db.Model): # Represents the assignment of a worker to a ShiftDefinition
    __tablename__ = 'scheduled_shift' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=True) # Nullable until assigned
    shift_definition_id = db.Column(db.Integer, db.ForeignKey('shift_definition.id'), nullable=False, unique=True) # Each defined slot gets one assignment entry

    def __repr__(self):
        slot_info = "Unknown Slot"
        if self.defined_slot: # Check if relationship is loaded
             slot_info = f"{self.defined_slot.name or self.defined_slot.id} ({self.defined_slot.slot_start_datetime.strftime('%Y-%m-%d %H:%M')})"
        worker_name = self.worker_assigned.name if self.worker_assigned else "UNASSIGNED"
        return f'<Assignment: Slot {slot_info} for {worker_name}>'

class User(db.Model): # For admin login (currently unused for authentication)
    __tablename__ = 'user' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))