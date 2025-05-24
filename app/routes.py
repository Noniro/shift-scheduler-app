from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app, session
from . import db
from .models import SchedulingPeriod, ShiftTemplate, ShiftDefinition, Worker, Constraint, ScheduledShift, User
from datetime import datetime, time, timedelta, date
from dateutil.parser import parse as parse_datetime

main_bp = Blueprint('main', __name__)

def get_active_period():
    active_period_id = session.get('active_period_id')
    if active_period_id:
        return SchedulingPeriod.query.get(active_period_id)
    return None

# --- User Name Routes ---
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
        # Check if actual shift definition slots have been generated for this period
        defined_shift_slots = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id).all()
        has_defined_shift_slots = bool(defined_shift_slots)

        if has_defined_shift_slots: # Only query assignments if slots exist
            scheduled_assignments = ScheduledShift.query.join(ShiftDefinition).\
                filter(ShiftDefinition.scheduling_period_id == active_period.id).\
                order_by(ShiftDefinition.slot_start_datetime).all()

    return render_template('index.html',
                           current_user_name=current_user_name,
                           active_period=active_period,
                           workers=workers,
                           scheduled_assignments=scheduled_assignments,
                           has_defined_shift_slots=has_defined_shift_slots)

@main_bp.route('/set_user_name', methods=['POST'])
def set_user_name():
    user_name = request.form.get('user_name')
    if user_name:
        session['user_name'] = user_name; session.permanent = True
        flash(f"Welcome, {user_name}! Your name is saved.", "success")
    else:
        flash("Please provide a name.", "warning")
    return redirect(url_for('main.index'))

@main_bp.route('/clear_name')
def clear_name():
    session.pop('user_name', None); flash("Your name has been cleared.", "info")
    return redirect(url_for('main.index'))

# --- Scheduling Period Routes ---
@main_bp.route('/periods', methods=['GET', 'POST'])
def manage_periods():
    if request.method == 'POST':
        try:
            name = request.form.get('period_name')
            start_date_str = request.form.get('period_start_date')
            end_date_str = request.form.get('period_end_date')
            start_time_str = request.form.get('period_start_time')
            end_time_str = request.form.get('period_end_time')

            if not all([name, start_date_str, end_date_str, start_time_str, end_time_str]):
                flash("All period fields are required.", "danger")
                return redirect(url_for('main.manage_periods'))

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
            db.session.add(new_period); db.session.commit()
            flash(f"Scheduling Period '{name}' created successfully.", "success")
            # Activate the new period and go to define templates
            session['active_period_id'] = new_period.id
            session.permanent = True
            return redirect(url_for('main.define_shift_templates', period_id=new_period.id))
        except ValueError as ve:
            flash(f"Invalid date or time format: {ve}", "danger")
        except Exception as e:
            db.session.rollback(); flash(f"Error creating period: {e}", "danger")
            current_app.logger.error(f"Error creating period: {e}\n{request.form}")
        return redirect(url_for('main.manage_periods'))

    periods = SchedulingPeriod.query.order_by(SchedulingPeriod.name).all()
    active_period_id = session.get('active_period_id')
    return render_template('manage_periods.html', periods=periods, active_period_id=active_period_id)

@main_bp.route('/set_active_period/<int:period_id>', methods=['POST'])
def set_active_period_action(period_id):
    period_to_activate = SchedulingPeriod.query.get_or_404(period_id)
    session['active_period_id'] = period_id
    session.permanent = True
    flash(f"Period '{period_to_activate.name}' is now active. You can now define its shift templates.", "info")
    # Redirect to define shift templates for the newly activated period
    return redirect(url_for('main.define_shift_templates', period_id=period_id))


@main_bp.route('/delete_period/<int:period_id>', methods=['POST'])
def delete_period(period_id):
    period_to_delete = SchedulingPeriod.query.get_or_404(period_id)
    if session.get('active_period_id') == period_id:
        session.pop('active_period_id', None)
    db.session.delete(period_to_delete); db.session.commit()
    flash(f"Period '{period_to_delete.name}' and all its data deleted.", "success")
    return redirect(url_for('main.manage_periods'))

# --- Shift Template and Slot Generation Routes ---
@main_bp.route('/period/<int:period_id>/define_shift_templates', methods=['GET', 'POST'])
def define_shift_templates(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    # Ensure this period is the one active in session, or make it so
    if session.get('active_period_id') != period_id:
        session['active_period_id'] = period_id
        session.permanent = True # Make session persistent
        flash(f"Active period switched to '{period.name}'.", "info")

    if request.method == 'POST': # For adding a new template
        try:
            name = request.form.get('template_name')
            if not name:
                flash("Template name is required.", "danger")
                return redirect(url_for('main.define_shift_templates', period_id=period.id))
                
            days = int(request.form.get('duration_days', 0))
            hours = int(request.form.get('duration_hours', 0))
            minutes = int(request.form.get('duration_minutes', 0))

            total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
            if total_duration_minutes < 20 : # As per user requirement
                flash("Minimum shift template duration is 20 minutes.", "danger")
            elif days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60: # Basic validation
                flash("Invalid duration values provided (e.g. hours must be 0-23).", "danger")
            else:
                new_template = ShiftTemplate(name=name, duration_days=days, duration_hours=hours, duration_minutes=minutes, scheduling_period_id=period.id)
                db.session.add(new_template); db.session.commit()
                flash(f"Shift template '{name}' added.", "success")
        except ValueError: flash("Invalid duration input. Please enter numbers.", "danger")
        except Exception as e:
            db.session.rollback(); flash(f"Error adding shift template: {e}", "danger")
            current_app.logger.error(f"Error adding template: {e}\n{request.form}")
        return redirect(url_for('main.define_shift_templates', period_id=period.id))

    templates = ShiftTemplate.query.filter_by(scheduling_period_id=period.id).order_by(ShiftTemplate.name).all()
    generated_slots = ShiftDefinition.query.filter_by(scheduling_period_id=period.id)\
                                           .order_by(ShiftDefinition.slot_start_datetime).all()
    has_generated_slots = bool(generated_slots)

    return render_template('define_shift_templates.html',
                           period=period,
                           templates=templates,
                           generated_slots=generated_slots, # Pass ordered list
                           has_generated_slots=has_generated_slots)


@main_bp.route('/period/<int:period_id>/delete_template/<int:template_id>', methods=['POST'])
def delete_shift_template(period_id, template_id):
    # Ensure period_id from URL matches template's period to prevent cross-period deletion
    template = ShiftTemplate.query.filter_by(id=template_id, scheduling_period_id=period_id).first_or_404()
    db.session.delete(template); db.session.commit()
    flash(f"Shift template '{template.name}' deleted. Re-generate slots if needed.", "info")
    return redirect(url_for('main.define_shift_templates', period_id=period_id))


@main_bp.route('/period/<int:period_id>/generate_coverage_slots', methods=['POST'])
def generate_coverage_slots_action(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    templates = ShiftTemplate.query.filter_by(scheduling_period_id=period.id).order_by(ShiftTemplate.id).all() # Or a defined fill_order

    if not templates:
        flash("No shift templates defined for this period. Cannot generate coverage slots.", "warning")
        return redirect(url_for('main.define_shift_templates', period_id=period.id))

    # Clear existing generated slots AND THEIR ASSIGNMENTS for this period before regenerating
    # Finding ScheduledShift IDs to delete based on ShiftDefinition's period_id
    ids_to_delete_assignments = [s.id for s in ScheduledShift.query.join(ShiftDefinition)
                                .filter(ShiftDefinition.scheduling_period_id == period_id).all()]
    if ids_to_delete_assignments:
        ScheduledShift.query.filter(ScheduledShift.id.in_(ids_to_delete_assignments)).delete(synchronize_session=False)
    
    ShiftDefinition.query.filter_by(scheduling_period_id=period.id).delete()
    db.session.commit() # Commit deletions first

    new_slots_generated_count = 0
    current_dt = period.period_start_datetime
    template_idx = 0
    
    # Safety break for very long periods or tiny shifts to prevent infinite loops in dev
    max_iterations = 10000 
    iterations = 0

    while current_dt < period.period_end_datetime and iterations < max_iterations :
        iterations += 1
        if not templates : break # Should be caught earlier
        
        template = templates[template_idx % len(templates)] # Cycle through templates
        duration = template.get_duration_timedelta()

        if duration.total_seconds() <= 0: # Skip templates with no duration
            current_app.logger.warning(f"Skipping template '{template.name}' with zero duration for period {period.id}")
            template_idx += 1
            if template_idx >= len(templates) * 2 and new_slots_generated_count == 0 : # Avoid infinite loop if all templates are zero duration
                 flash("All templates have zero duration. Cannot generate slots.", "danger")
                 return redirect(url_for('main.define_shift_templates', period_id=period.id))
            continue


        slot_start = current_dt
        slot_end = current_dt + duration

        if slot_end > period.period_end_datetime:
            slot_end = period.period_end_datetime # Cap slot end at period end
        
        if slot_start < slot_end: # Only create slot if it has a positive duration
            new_slot = ShiftDefinition(
                slot_start_datetime=slot_start,
                slot_end_datetime=slot_end,
                scheduling_period_id=period.id,
                generated_from_template_id=template.id
            )
            db.session.add(new_slot)
            new_slots_generated_count +=1
        
        current_dt = slot_end # Advance current time to the end of the created slot
        template_idx += 1 # Move to next template in cycle

        if current_dt >= period.period_end_datetime:
            break # Explicitly break if we've reached or passed the end

    if iterations >= max_iterations:
        flash(f"Slot generation stopped after {max_iterations} iterations to prevent a potential infinite loop. Please check period duration and shift templates.", "danger")
        current_app.logger.error(f"Max iterations reached for period {period.id}. Slots generated: {new_slots_generated_count}")


    if new_slots_generated_count > 0:
        db.session.commit()
        flash(f"{new_slots_generated_count} coverage slots generated (or re-generated) for period '{period.name}'.", "success")
    else:
        flash("No new coverage slots were generated. This might be due to period duration, template durations, or reaching max iterations.", "warning")

    return redirect(url_for('main.define_shift_templates', period_id=period.id))


# --- Worker and Constraint Routes (same as previous correct version) ---
@main_bp.route('/add_worker', methods=['POST'])
def add_worker():
    name = request.form.get('worker_name')
    email_from_form = request.form.get('worker_email')
    max_hours_str = request.form.get('max_hours_per_week')
    max_hours = int(max_hours_str) if max_hours_str and max_hours_str.isdigit() else None

    if not name:
        flash('Worker name is required.', 'danger'); return redirect(url_for('main.index'))

    processed_email = email_from_form.strip() if email_from_form else None
    if not processed_email: processed_email = None

    if Worker.query.filter_by(name=name).first():
        flash(f'Worker with name "{name}" already exists.', 'warning'); return redirect(url_for('main.index'))
    if processed_email and Worker.query.filter_by(email=processed_email).first():
        flash(f'Worker with email "{processed_email}" already exists.', 'warning'); return redirect(url_for('main.index'))
    
    try:
        worker = Worker(name=name, email=processed_email, max_hours_per_week=max_hours)
        db.session.add(worker); db.session.commit()
        flash(f'Worker "{name}" added successfully.', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Error adding worker: {e}', 'danger')
        current_app.logger.error(f"Error adding worker {name}: {e}")
    return redirect(url_for('main.index'))

@main_bp.route('/worker/<int:worker_id>/add_constraint', methods=['POST'])
def add_constraint(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    try:
        start_date_str = request.form.get('constraint_start_date')
        end_date_str = request.form.get('constraint_end_date')
        if not start_date_str or not end_date_str:
            flash("Both start and end dates for unavailability are required.", "danger"); return redirect(url_for('main.index'))
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if end_date_obj < start_date_obj:
            flash("End date cannot be before start date.", "danger"); return redirect(url_for('main.index'))
        cs_dt = datetime.combine(start_date_obj, time.min); ce_dt = datetime.combine(end_date_obj, time.max)
        constraint = Constraint(worker_id=worker.id, constraint_type="UNAVAILABLE_DAY_RANGE", start_datetime=cs_dt, end_datetime=ce_dt)
        db.session.add(constraint); db.session.commit()
        flash(f'Unavailability added for {worker.name}.', 'success')
    except ValueError: flash("Invalid date format for unavailability.", "danger")
    except Exception as e:
        db.session.rollback(); flash(f'Error adding constraint: {e}', 'danger')
        current_app.logger.error(f"Error in add_constraint: {e}\n{request.form}")
    return redirect(url_for('main.index'))

# --- Schedule Generation Route ---
@main_bp.route('/generate_schedule', methods=['POST'])
def generate_schedule_route():
    active_period = get_active_period()
    if not active_period:
        flash("No active scheduling period.", "danger"); return redirect(url_for('main.manage_periods'))

    ids_to_delete = [s.id for s in ScheduledShift.query.join(ShiftDefinition).filter(ShiftDefinition.scheduling_period_id == active_period.id).all()]
    if ids_to_delete:
        ScheduledShift.query.filter(ScheduledShift.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()

    workers = Worker.query.all()
    defined_slots_to_fill = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id).order_by(ShiftDefinition.slot_start_datetime).all()

    if not defined_slots_to_fill:
        flash(f"No coverage slots generated for '{active_period.name}'.", "warning")
        return redirect(url_for('main.define_shift_templates', period_id=active_period.id))
    if not workers:
        flash("No workers added.", "warning"); return redirect(url_for('main.index'))

    assignments_to_make = [ScheduledShift(shift_definition_id=slot_def.id) for slot_def in defined_slots_to_fill]
    if assignments_to_make:
        db.session.add_all(assignments_to_make); db.session.commit()
    else:
        flash("No assignment placeholders to create, though slots were defined.", "warning"); return redirect(url_for('main.index'))

    from .algorithm import assign_shifts_fairly
    all_pending_assignments = ScheduledShift.query.join(ShiftDefinition)\
        .filter(ShiftDefinition.scheduling_period_id == active_period.id, ScheduledShift.worker_id.is_(None))\
        .all()

    _successful_assignment, algo_messages = assign_shifts_fairly(all_pending_assignments, workers, active_period)
    for msg_type, msg_text in algo_messages: flash(msg_text, msg_type)
    return redirect(url_for('main.index'))