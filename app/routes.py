from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app, session
from . import db
from .models import SchedulingPeriod, ShiftTemplate, ShiftDefinition, Worker, Constraint, ScheduledShift # Added SchedulingPeriod, ShiftTemplate
from datetime import datetime, time, timedelta, date
from dateutil.parser import parse as parse_datetime

main_bp = Blueprint('main', __name__)

def get_active_period():
    active_period_id = session.get('active_period_id')
    if active_period_id:
        return SchedulingPeriod.query.get(active_period_id)
    return None

# --- User Name Routes (same as before) ---
@main_bp.route('/', methods=['GET', 'POST'])
def index():
    current_user_name = session.get('user_name')
    if request.method == 'POST' and 'user_name' in request.form and not current_user_name:
        session['user_name'] = request.form['user_name']
        session.permanent = True
        flash(f"Great to meet you, {session['user_name']}!", "success")
        return redirect(url_for('main.index'))

    active_period = get_active_period()
    workers = Worker.query.order_by(Worker.name).all()
    scheduled_assignments = []
    has_defined_shift_slots = False

    if active_period:
        # Get actual generated slots for the active period
        defined_shift_slots = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id).all()
        has_defined_shift_slots = bool(defined_shift_slots)

        # Get assignments for these slots
        if has_defined_shift_slots:
            scheduled_assignments = ScheduledShift.query.join(ShiftDefinition).\
                filter(ShiftDefinition.scheduling_period_id == active_period.id).\
                order_by(ShiftDefinition.slot_start_datetime).all()

    return render_template('index.html',
                           current_user_name=current_user_name,
                           active_period=active_period,
                           workers=workers,
                           scheduled_assignments=scheduled_assignments,
                           has_defined_shift_slots=has_defined_shift_slots) # To know if "Generate" button should be active

@main_bp.route('/set_user_name', methods=['POST']) # Same as before
def set_user_name():
    user_name = request.form.get('user_name')
    if user_name:
        session['user_name'] = user_name; session.permanent = True
        flash(f"Welcome, {user_name}! Your name is saved.", "success")
    return redirect(url_for('main.index'))

@main_bp.route('/clear_name') # Same as before
def clear_name():
    session.pop('user_name', None); flash("Your name has been cleared.", "info")
    return redirect(url_for('main.index'))

# --- Scheduling Period Routes ---
@main_bp.route('/periods', methods=['GET', 'POST'])
def manage_periods():
    if request.method == 'POST': # Create new period
        try:
            name = request.form['period_name']
            start_date_str = request.form['period_start_date'] # From Litepicker's hidden input
            end_date_str = request.form['period_end_date']
            start_time_str = request.form['period_start_time']
            end_time_str = request.form['period_end_time']

            if SchedulingPeriod.query.filter_by(name=name).first():
                flash(f"A scheduling period with the name '{name}' already exists.", "danger")
                return redirect(url_for('main.manage_periods'))

            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()

            if end_date_obj < start_date_obj or \
               (end_date_obj == start_date_obj and end_time_obj <= start_time_obj):
                flash("Period end must be after period start.", "danger")
                return redirect(url_for('main.manage_periods'))

            period_start_dt = datetime.combine(start_date_obj, start_time_obj)
            period_end_dt = datetime.combine(end_date_obj, end_time_obj)

            new_period = SchedulingPeriod(name=name, period_start_datetime=period_start_dt, period_end_datetime=period_end_dt)
            db.session.add(new_period)
            db.session.commit()
            flash(f"Scheduling Period '{name}' created successfully.", "success")
            # Optionally, make the newly created period active
            # set_active_period_action(new_period.id)
            return redirect(url_for('main.manage_periods'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating period: {e}", "danger")
            current_app.logger.error(f"Error creating period: {e}\n{request.form}")

    periods = SchedulingPeriod.query.order_by(SchedulingPeriod.name).all()
    active_period_id = session.get('active_period_id')
    return render_template('manage_periods.html', periods=periods, active_period_id=active_period_id)

@main_bp.route('/set_active_period/<int:period_id>', methods=['POST'])
def set_active_period_action(period_id):
    period_to_activate = SchedulingPeriod.query.get_or_404(period_id)
    
    # Deactivate any other currently active period (optional, if only one can be truly "active" globally)
    # SchedulingPeriod.query.update({SchedulingPeriod.is_active: False})
    # period_to_activate.is_active = True
    # db.session.commit()
    
    session['active_period_id'] = period_id
    session.permanent = True
    flash(f"Period '{period_to_activate.name}' is now active.", "info")
    return redirect(request.referrer or url_for('main.index')) # Go back or to index

@main_bp.route('/delete_period/<int:period_id>', methods=['POST'])
def delete_period(period_id):
    period_to_delete = SchedulingPeriod.query.get_or_404(period_id)
    if session.get('active_period_id') == period_id:
        session.pop('active_period_id', None)
    # Cascading delete should handle related ShiftTemplates and ShiftDefinitions
    db.session.delete(period_to_delete)
    db.session.commit()
    flash(f"Period '{period_to_delete.name}' and all its data deleted.", "success")
    return redirect(url_for('main.manage_periods'))


# --- Shift Template and Slot Generation Routes ---
@main_bp.route('/period/<int:period_id>/define_shift_templates', methods=['GET', 'POST'])
def define_shift_templates(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    if session.get('active_period_id') != period_id: # Ensure consistency
        session['active_period_id'] = period_id # Or redirect/error
        flash(f"Switched active period to '{period.name}'.", "info")

    if request.method == 'POST':
        try:
            name = request.form['template_name']
            days = int(request.form.get('duration_days', 0))
            hours = int(request.form.get('duration_hours', 0))
            minutes = int(request.form.get('duration_minutes', 0))

            if days == 0 and hours == 0 and minutes < 20:
                flash("Minimum shift template duration is 20 minutes.", "danger")
            elif days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60:
                flash("Invalid duration values provided.", "danger")
            else:
                total_minutes = (days * 24 * 60) + (hours * 60) + minutes
                if total_minutes == 0 :
                    flash("Shift template duration cannot be zero.", "danger")
                else:
                    new_template = ShiftTemplate(
                        name=name,
                        duration_days=days,
                        duration_hours=hours,
                        duration_minutes=minutes,
                        scheduling_period_id=period.id
                    )
                    db.session.add(new_template)
                    db.session.commit()
                    flash(f"Shift template '{name}' added.", "success")
        except ValueError:
            flash("Invalid duration input. Please enter numbers.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding shift template: {e}", "danger")
            current_app.logger.error(f"Error adding template: {e}\n{request.form}")
        return redirect(url_for('main.define_shift_templates', period_id=period.id))

    templates = ShiftTemplate.query.filter_by(scheduling_period_id=period.id).all()
    # Check if actual shift definition slots have been generated for this period
    has_generated_slots = ShiftDefinition.query.filter_by(scheduling_period_id=period.id).first() is not None
    return render_template('define_shift_templates.html', period=period, templates=templates, has_generated_slots=has_generated_slots)

@main_bp.route('/period/<int:period_id>/delete_template/<int:template_id>', methods=['POST'])
def delete_shift_template(period_id, template_id):
    template = ShiftTemplate.query.filter_by(id=template_id, scheduling_period_id=period_id).first_or_404()
    # If slots were generated from this template, deleting the template might orphan them
    # or you might want to delete those slots too (more complex logic).
    # For now, just delete the template. Any generated slots will lose their template link name.
    db.session.delete(template)
    db.session.commit()
    flash(f"Shift template '{template.name}' deleted. Re-generate slots if needed.", "info")
    return redirect(url_for('main.define_shift_templates', period_id=period_id))


@main_bp.route('/period/<int:period_id>/generate_coverage_slots', methods=['POST'])
def generate_coverage_slots_action(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    templates = ShiftTemplate.query.filter_by(scheduling_period_id=period.id).order_by(ShiftTemplate.id).all() # Or by fill_order

    if not templates:
        flash("No shift templates defined for this period. Cannot generate coverage slots.", "warning")
        return redirect(url_for('main.define_shift_templates', period_id=period.id))

    # Clear existing generated slots for this period before regenerating
    ShiftDefinition.query.filter_by(scheduling_period_id=period.id).delete()
    # Also clear any assignments for those old slots
    # This needs to be done carefully. If ShiftDefinition has a cascade to ScheduledShift, it's handled.
    # If not, you'd query ScheduledShift JOIN ShiftDefinition WHERE scheduling_period_id = period_id and delete.
    # The model's cascade should handle it.
    db.session.commit()

    new_slots_generated = 0
    current_datetime = period.period_start_datetime
    template_index = 0

    while current_datetime < period.period_end_datetime:
        if not templates: break # Should not happen if checked before, but safeguard
        
        template = templates[template_index % len(templates)] # Cycle through templates
        duration = template.get_duration_timedelta()

        slot_start = current_datetime
        slot_end = current_datetime + duration

        # Ensure the slot does not exceed the period's end time
        if slot_end > period.period_end_datetime:
            slot_end = period.period_end_datetime
        
        if slot_start < slot_end : # Only create if there's actual time
            new_slot = ShiftDefinition(
                slot_start_datetime=slot_start,
                slot_end_datetime=slot_end,
                scheduling_period_id=period.id,
                generated_from_template_id=template.id
            )
            db.session.add(new_slot)
            new_slots_generated +=1
        
        current_datetime = slot_end
        template_index += 1 # Move to next template in cycle or restart cycle

    if new_slots_generated > 0:
        db.session.commit()
        flash(f"{new_slots_generated} coverage slots generated for period '{period.name}' based on templates.", "success")
    else:
        flash(f"No new coverage slots were generated. Check period duration and templates. Start: {period.period_start_datetime}, End: {period.period_end_datetime}", "warning")

    return redirect(url_for('main.define_shift_templates', period_id=period.id))


# --- Worker and Constraint Routes (largely same as before, but ensure they operate within active_period context if needed) ---
@main_bp.route('/add_worker', methods=['POST']) # Same as before
def add_worker():
    name = request.form['worker_name']
    email = request.form['worker_email']
    max_hours_str = request.form.get('max_hours_per_week')
    max_hours = int(max_hours_str) if max_hours_str and max_hours_str.isdigit() else None

    if Worker.query.filter_by(email=email).first():
        flash(f'Worker with email {email} already exists.', 'warning')
    elif Worker.query.filter_by(name=name).first():
        flash(f'Worker with name {name} already exists.', 'warning')
    else:
        worker = Worker(name=name, email=email, max_hours_per_week=max_hours)
        db.session.add(worker)
        db.session.commit()
        flash(f'Worker {name} added.', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/worker/<int:worker_id>/add_constraint', methods=['POST']) # Same as before
def add_constraint(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    try:
        start_date_str = request.form['constraint_start_date']
        end_date_str = request.form['constraint_end_date']
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if end_date_obj < start_date_obj:
            flash("End date cannot be before start date for unavailability.", "danger"); return redirect(url_for('main.index'))

        constraint_start_dt = datetime.combine(start_date_obj, time.min)
        constraint_end_dt = datetime.combine(end_date_obj, time.max)
        constraint = Constraint(worker_id=worker.id, constraint_type="UNAVAILABLE_DAY_RANGE",
                                start_datetime=constraint_start_dt, end_datetime=constraint_end_dt)
        db.session.add(constraint); db.session.commit()
        flash(f'Unavailability from {start_date_str} to {end_date_str} added for {worker.name}.', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Error adding constraint: {e}', 'danger')
        current_app.logger.error(f"Error in add_constraint: {e}\n{request.form}")
    return redirect(url_for('main.index'))

# --- Schedule Generation Route ---
@main_bp.route('/generate_schedule', methods=['POST'])
def generate_schedule_route():
    active_period = get_active_period()
    if not active_period:
        flash("No active scheduling period. Cannot generate schedule.", "danger")
        return redirect(url_for('main.manage_periods'))

    # 1. Clear any previously generated assignments FOR THIS PERIOD
    # This requires joining ScheduledShift with ShiftDefinition to filter by period_id
    existing_assignments = ScheduledShift.query \
        .join(ScheduledShift.defined_slot) \
        .filter(ShiftDefinition.scheduling_period_id == active_period.id) \
        .all()
    for ass in existing_assignments:
        db.session.delete(ass)
    db.session.commit()


    workers = Worker.query.all()
    # Get the actual generated coverage slots for the active period
    defined_slots_to_fill = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id)\
                                                 .order_by(ShiftDefinition.slot_start_datetime).all()

    if not defined_slots_to_fill:
        flash(f"No coverage slots have been generated for period '{active_period.name}'. Please generate them first.", "warning")
        return redirect(url_for('main.define_shift_templates', period_id=active_period.id))
    if not workers:
        flash("No workers have been added. Please add workers first.", "warning")
        return redirect(url_for('main.index'))

    assignments_to_make = []
    for slot_def in defined_slots_to_fill:
        assignment = ScheduledShift(shift_definition_id=slot_def.id) # Link to the specific ShiftDefinition slot
        assignments_to_make.append(assignment)
    
    if assignments_to_make:
        db.session.add_all(assignments_to_make)
        db.session.commit() # Get IDs for placeholder assignments
    else:
        flash("No assignments to make, though slots were defined. Check data.", "warning")
        return redirect(url_for('main.index'))

    from .algorithm import assign_shifts_fairly
    all_pending_assignments = ScheduledShift.query.join(ShiftDefinition)\
                                .filter(ShiftDefinition.scheduling_period_id == active_period.id, ScheduledShift.worker_id == None)\
                                .all()

    successful_assignment, algo_messages = assign_shifts_fairly(all_pending_assignments, workers, active_period)

    for msg_type, msg_text in algo_messages:
        flash(msg_text, msg_type)

    # No specific success/warning here as algo_messages handles it
    # if successful_assignment:
    #     flash('Schedule generation process complete.', 'success')
    # else:
    #     flash('Schedule generation process completed with issues. Some shifts may be unassigned.', 'warning')

    return redirect(url_for('main.index'))