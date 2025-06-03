from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app, session
from . import db
from .models import SchedulingPeriod, JobRole, ShiftDefinition, Worker, Constraint, ScheduledShift, User
from datetime import datetime, time, timedelta, date
from dateutil.parser import parse as parse_datetime
from sqlalchemy.orm import joinedload, selectinload # For eager loading

# Option 1 - copilot 
"""
This file contains the main application routes for handling user interactions,
scheduling periods, job roles, workers, and shift assignments.

It includes routes for:
- Setting and clearing user names
- Managing scheduling periods
- Creating and managing job roles
- Generating shift slots
- Managing workers and their constraints
- Assigning shifts to workers based on constraints and qualifications
- etc...

This file is part of a Flask application that manages scheduling for workers in various job roles.

It uses SQLAlchemy for ORM and Flask's session management for user state.
It is designed to be modular, with routes grouped logically for easier maintenance and readability.
It also includes error handling and logging for better debugging and user feedback.
"""



# Option 2 - aistudion - google 
"""
routes.py - Defines the web routes and view functions for the Flask application.

This module is responsible for handling incoming HTTP requests and routing them
to the appropriate Python functions (view functions). These functions then
interact with the database models (from `app.models`), process user input,
manage session data, and render HTML templates to be sent back to the client's
browser.

The routes are organized using a Flask Blueprint named 'main_bp'.

Key functionalities handled by this module include:

1.  **User Identification:**
    -   Displaying the main page (`/`).
    -   Allowing users to set and clear their name, which is stored in the session.

2.  **Scheduling Period Management (`/periods`, etc.):**
    -   Creating new scheduling periods with start and end datetimes.
    -   Listing existing periods.
    -   Setting a period as "active" (stored in session), which contexts other operations.
    -   Deleting scheduling periods and their associated data (job roles, slots, assignments).

3.  **Job Role Management (within an active period) (`/period/<id>/roles`, etc.):**
    -   Adding job roles (e.g., "Cook", "Server") to the active scheduling period.
    -   Defining properties for each role like number needed and default shift duration.
    -   Listing and deleting job roles for the active period.

4.  **Coverage Slot Generation (`/period/<id>/generate_slots`):**
    -   Automatically generating individual `ShiftDefinition` (coverage slot) instances
        based on the job roles defined for the active period, their durations,
        and the period's start/end times.
    -   This process first clears any existing slots for the period.

5.  **Worker Management (`/manage_workers`, etc.):**
    -   Adding new workers to the system.
    -   Listing existing workers.
    -   Deleting workers.
    -   Editing a worker's qualified job roles for the currently active period.
    -   Adding unavailability constraints for workers (e.g., specific days they cannot work).

6.  **Shift Assignment (`/period/<id>/generate_slots_and_assign`):**
    -   A comprehensive action that combines:
        - Clearing old slots and assignments for the active period.
        - Generating new `ShiftDefinition` (coverage) slots.
        - Creating placeholder `ScheduledShift` objects for these new slots.
        - Invoking the shift assignment algorithm (`assign_shifts_fairly` from `app.algorithm`)
          to attempt to assign workers to the unassigned `ScheduledShift` placeholders.
    -   The main page (`/`) also displays the current schedule for the active period.

Helper Functions:
-   `get_active_period()`: Retrieves the currently active `SchedulingPeriod` object
    based on an ID stored in the user's session.

Common patterns used:
-   Flask's `render_template()` to display HTML pages.
-   `request.form` to access data from submitted HTML forms.
-   `redirect(url_for(...))` for Post/Redirect/Get pattern.
-   `flash()` messages for user feedback.
-   `session` object for storing user-specific data (user name, active period ID).
-   SQLAlchemy ORM for database interactions (queries, adding, committing, deleting objects).
-   Eager loading (`selectinload`, `joinedload`) for optimizing database queries,
    especially when displaying lists of related objects.
-   Error handling using try-except blocks and logging with `current_app.logger`.
"""

main_bp = Blueprint('main', __name__)

def get_active_period():
    active_period_id = session.get('active_period_id')
    if active_period_id:
        # FIX: Remove .options(selectinload(SchedulingPeriod.job_roles)) when using .get()
        # The lazy='dynamic' on job_roles means it's a query object already.
        # Accessing period.job_roles.count() later will execute an efficient count query.
        return SchedulingPeriod.query.get(active_period_id)
    return None

# --- User Name Routes ---
@main_bp.route('/', methods=['GET', 'POST'])
def index():
    current_user_name = session.get('user_name')
    if request.method == 'POST' and 'user_name_field' in request.form and not current_user_name:
        name_input = request.form.get('user_name_field')
        if name_input and name_input.strip(): # Ensure name is not just whitespace
            session['user_name'] = name_input.strip()
            session.permanent = True
            flash(f"Great to meet you, {session['user_name']}!", "success")
        else:
            flash("Please enter your name.", "warning")
        return redirect(url_for('main.index'))

    active_period = get_active_period()
    # Eager load qualified_roles for each worker
    workers = Worker.query.options(selectinload(Worker.qualified_roles)).order_by(Worker.name).all()
    
    scheduled_assignments = []
    has_defined_shift_slots = False # Slots are ShiftDefinition instances

    if active_period:
        has_defined_shift_slots = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id).first() is not None
        if has_defined_shift_slots:
            scheduled_assignments = ScheduledShift.query.options(
                    joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role), # Eager load job_role
                    joinedload(ScheduledShift.worker_assigned)
                ).join(ShiftDefinition).\
                filter(ShiftDefinition.scheduling_period_id == active_period.id).\
                order_by(ShiftDefinition.slot_start_datetime, ShiftDefinition.job_role_id, ShiftDefinition.instance_number).all()

    return render_template('index.html',
                           current_user_name=current_user_name,
                           active_period=active_period,
                           workers=workers,
                           scheduled_assignments=scheduled_assignments,
                           has_defined_shift_slots=has_defined_shift_slots)

@main_bp.route('/set_user_name', methods=['POST'])
def set_user_name():
    user_name = request.form.get('user_name_field')
    if user_name and user_name.strip():
        session['user_name'] = user_name.strip(); session.permanent = True
        flash(f"Welcome, {user_name.strip()}! Your name is saved.", "success")
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
            start_date_str = request.form.get('period_start_date_hidden')
            end_date_str = request.form.get('period_end_date_hidden')
            start_time_str = request.form.get('period_start_time')
            end_time_str = request.form.get('period_end_time')

            if not name or not name.strip():
                flash("Period name is required.", "danger")
                return redirect(url_for('main.manage_periods'))
            name = name.strip()


            if not all([start_date_str, end_date_str, start_time_str, end_time_str]):
                flash("All period date and time fields are required.", "danger")
                return redirect(url_for('main.manage_periods'))

            if SchedulingPeriod.query.filter(SchedulingPeriod.name.ilike(name)).first():
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
            
            new_period = SchedulingPeriod(
                name=name, 
                period_start_datetime=period_start_dt, 
                period_end_datetime=period_end_dt
            )

            db.session.add(new_period); db.session.commit()
            flash(f"Scheduling Period '{name}' created. Now define its job roles.", "success")
            session['active_period_id'] = new_period.id
            session.permanent = True
            return redirect(url_for('main.manage_job_roles_for_period', period_id=new_period.id))
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
    flash(f"Period '{period_to_activate.name}' is now active. You can now define its job roles and shift slots.", "info")
    return redirect(url_for('main.manage_job_roles_for_period', period_id=period_id))

@main_bp.route('/delete_period/<int:period_id>', methods=['POST'])
def delete_period(period_id):
    period_to_delete = SchedulingPeriod.query.get_or_404(period_id)
    if session.get('active_period_id') == period_id:
        session.pop('active_period_id', None)
    db.session.delete(period_to_delete); db.session.commit()
    flash(f"Period '{period_to_delete.name}' and all its associated data deleted.", "success")
    return redirect(url_for('main.manage_periods'))

# --- Job Role and Slot Generation Routes ---
@main_bp.route('/period/<int:period_id>/roles', methods=['GET', 'POST'])
def manage_job_roles_for_period(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    if session.get('active_period_id') != period_id:
        session['active_period_id'] = period_id; session.permanent = True
        flash(f"Active period set to '{period.name}'.", "info")

    if request.method == 'POST':
        # ... (POST logic for adding a job role - REMAINS THE SAME) ...
        try:
            role_name = request.form.get('role_name')
            number_needed_str = request.form.get('number_needed', '1')
            days_str = request.form.get('duration_days', '0')
            hours_str = request.form.get('duration_hours', '0')
            minutes_str = request.form.get('duration_minutes', '0')
            if not role_name or not role_name.strip(): flash("Job role name is required.", "danger")
            else:
                role_name = role_name.strip(); number_needed = int(number_needed_str)
                days = int(days_str); hours = int(hours_str); minutes = int(minutes_str)
                if number_needed < 1: flash("Number needed must be at least 1.", "danger")
                else:
                    total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
                    if total_duration_minutes < 20: flash("Minimum shift duration for a role is 20 minutes.", "danger")
                    elif days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60: flash("Invalid duration values (e.g., hours 0-23, minutes 0-59).", "danger")
                    elif JobRole.query.filter_by(scheduling_period_id=period.id, name=role_name).first(): flash(f"Job role '{role_name}' already exists for this period.", "warning")
                    else:
                        new_role = JobRole(name=role_name, number_needed=number_needed, shift_duration_days=days, shift_duration_hours=hours, shift_duration_minutes=minutes, scheduling_period_id=period.id)
                        db.session.add(new_role); db.session.commit(); flash(f"Job Role '{role_name}' added to period '{period.name}'.", "success")
        except ValueError: flash("Invalid number for 'Needed' or 'Duration' fields.", "danger")
        except Exception as e: db.session.rollback(); flash(f"Error adding job role: {e}", "danger"); current_app.logger.error(f"Error adding job role for period {period.id}: {e}\n{request.form}")
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    job_roles = JobRole.query.filter_by(scheduling_period_id=period.id).order_by(JobRole.name).all()
    generated_slots = ShiftDefinition.query.options(joinedload(ShiftDefinition.job_role))\
                                           .filter_by(scheduling_period_id=period.id)\
                                           .order_by(ShiftDefinition.job_role_id, ShiftDefinition.instance_number, ShiftDefinition.slot_start_datetime).all()
    has_generated_slots = bool(generated_slots)
    workers_exist = Worker.query.first() is not None
    can_assign = workers_exist and job_roles

    # ---- RETRIEVE DETAILED MESSAGES FROM SESSION ----
    assignment_details = session.pop('assignment_details', None) # Get and remove from session
    # ---- END OF RETRIEVAL ----

    return render_template('manage_job_roles.html', 
                           period=period, 
                           job_roles=job_roles, 
                           generated_slots=generated_slots,
                           has_generated_slots=has_generated_slots,
                           can_assign=can_assign,
                           assignment_details=assignment_details) # Pass to template



@main_bp.route('/period/<int:period_id>/role/<int:role_id>/delete', methods=['POST'])
def delete_job_role(period_id, role_id):
    role = JobRole.query.filter_by(id=role_id, scheduling_period_id=period_id).first_or_404()
    db.session.delete(role); db.session.commit()
    flash(f"Job Role '{role.name}' and its generated slots/assignments deleted.", "info")
    return redirect(url_for('main.manage_job_roles_for_period', period_id=period_id))


@main_bp.route('/period/<int:period_id>/generate_slots', methods=['POST'])
def generate_coverage_slots_for_period(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    job_roles_for_period = JobRole.query.filter_by(scheduling_period_id=period.id).all()

    if not job_roles_for_period:
        flash("No job roles defined for this period. Cannot generate coverage slots.", "warning")
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    ids_to_delete_assignments = [s.id for s in ScheduledShift.query.join(ShiftDefinition)
                               .filter(ShiftDefinition.scheduling_period_id == period_id).all()]
    if ids_to_delete_assignments:
        ScheduledShift.query.filter(ScheduledShift.id.in_(ids_to_delete_assignments)).delete(synchronize_session=False)
    ShiftDefinition.query.filter_by(scheduling_period_id=period.id).delete()
    db.session.commit()

    total_new_slots_generated = 0
    for role in job_roles_for_period:
        role_slots_generated = 0
        current_dt_for_role = period.period_start_datetime
        duration = role.get_duration_timedelta()

        if duration.total_seconds() <= 0:
            current_app.logger.warning(f"Skipping role '{role.name}' due to zero duration."); continue

        max_iter = 5000; iter_count = 0 
        while current_dt_for_role < period.period_end_datetime and iter_count < max_iter:
            iter_count += 1
            slot_start = current_dt_for_role
            slot_end = current_dt_for_role + duration
            if slot_end > period.period_end_datetime: slot_end = period.period_end_datetime
            
            if slot_start < slot_end:
                for i in range(1, role.number_needed + 1):
                    new_slot = ShiftDefinition(slot_start_datetime=slot_start, slot_end_datetime=slot_end,
                                               instance_number=i, scheduling_period_id=period.id, job_role_id=role.id)
                    db.session.add(new_slot)
                    role_slots_generated +=1
            current_dt_for_role = slot_end
            if current_dt_for_role >= period.period_end_datetime: break
        if iter_count >= max_iter: flash(f"Max iterations for role '{role.name}'.", "warning")
        total_new_slots_generated += role_slots_generated

    if total_new_slots_generated > 0:
        try:
            db.session.commit(); flash(f"{total_new_slots_generated} slots generated for '{period.name}'.", "success")
        except Exception as e:
            db.session.rollback(); flash(f"Error committing slots: {e}", "danger")
            current_app.logger.error(f"Error committing slots for period {period.id}: {e}")
    else:
        flash("No new slots generated. Check role durations.", "warning")
    return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))


# --- Worker and Constraint Routes ---
@main_bp.route('/manage_workers', methods=['GET', 'POST'])
def manage_workers():
    active_period = get_active_period()
    all_job_roles_in_active_period = []
    if active_period:
        all_job_roles_in_active_period = JobRole.query.filter_by(scheduling_period_id=active_period.id).order_by(JobRole.name).all()
    
    if request.method == 'POST':
        # ... (POST logic remains the same as your last full version) ...
        name = request.form.get('worker_name')
        email_from_form = request.form.get('worker_email')
        max_hours_str = request.form.get('max_hours_per_week')
        max_hours = int(max_hours_str) if max_hours_str and max_hours_str.isdigit() else None
        qualified_role_ids_str = request.form.getlist('qualified_roles') 

        if not name or not name.strip():
            flash('Worker name is required.', 'danger'); return redirect(url_for('main.manage_workers'))
        name = name.strip()

        processed_email = email_from_form.strip() if email_from_form else None
        if not processed_email: processed_email = None

        if Worker.query.filter(Worker.name.ilike(name)).first():
            flash(f'Worker with name "{name}" already exists.', 'warning'); return redirect(url_for('main.manage_workers'))
        if processed_email and Worker.query.filter(Worker.email.ilike(processed_email)).first():
            flash(f'Worker with email "{processed_email}" already exists.', 'warning'); return redirect(url_for('main.manage_workers'))
        
        try:
            new_worker = Worker(name=name, email=processed_email, max_hours_per_week=max_hours)
            if active_period and qualified_role_ids_str:
                qualified_role_ids = [int(r_id) for r_id in qualified_role_ids_str]
                roles_to_assign = JobRole.query.filter(
                    JobRole.id.in_(qualified_role_ids),
                    JobRole.scheduling_period_id == active_period.id 
                ).all()
                for role in roles_to_assign:
                    new_worker.qualified_roles.append(role)
            
            db.session.add(new_worker); db.session.commit()
            flash(f'Worker "{name}" added successfully.', 'success')
        except Exception as e:
            db.session.rollback(); flash(f'Error adding worker: {e}', 'danger')
            current_app.logger.error(f"Error adding worker {name}: {e}")
        return redirect(url_for('main.manage_workers'))

    # ---- FIX IS HERE for the GET request part ----
    workers = Worker.query.options(
        selectinload(Worker.qualified_roles).selectinload(JobRole.scheduling_period)
        # REMOVE: selectinload(Worker.constraints) 
    ).order_by(Worker.name).all()
    # ---- END OF FIX ----
    
    return render_template('manage_workers.html', workers=workers, active_period=active_period, 
                           all_job_roles_in_active_period=all_job_roles_in_active_period)

@main_bp.route('/worker/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    db.session.delete(worker); db.session.commit()
    flash(f"Worker '{worker.name}' deleted.", "info")
    return redirect(url_for('main.manage_workers'))


@main_bp.route('/worker/<int:worker_id>/edit_roles', methods=['POST'])
def edit_worker_roles(worker_id):
    worker = Worker.query.options(selectinload(Worker.qualified_roles)).get_or_404(worker_id)
    active_period = get_active_period()
    if not active_period:
        flash("No active period to manage roles for.", "warning"); return redirect(url_for('main.manage_workers'))

    submitted_role_ids = set(map(int, request.form.getlist('qualified_roles')))
    
    current_period_roles_for_worker = {role.id for role in worker.qualified_roles if role.scheduling_period_id == active_period.id}
    
    for role_id_to_remove in current_period_roles_for_worker - submitted_role_ids:
        role = JobRole.query.get(role_id_to_remove)
        if role and role in worker.qualified_roles:
            worker.qualified_roles.remove(role)
            
    for role_id_to_add in submitted_role_ids - current_period_roles_for_worker:
        role = JobRole.query.filter_by(id=role_id_to_add, scheduling_period_id=active_period.id).first()
        if role and role not in worker.qualified_roles:
             worker.qualified_roles.append(role)
             
    try:
        db.session.commit(); flash(f"Roles updated for worker {worker.name} for period '{active_period.name}'.", "success")
    except Exception as e:
        db.session.rollback(); flash(f"Error updating roles: {e}", "danger")
        current_app.logger.error(f"Error updating roles for worker {worker.id}: {e}")
    return redirect(url_for('main.manage_workers'))


@main_bp.route('/worker/<int:worker_id>/add_constraint', methods=['POST'])
def add_constraint(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    target_redirect = request.form.get('redirect_to', url_for('main.manage_workers'))
    try:
        start_date_str = request.form.get('constraint_start_date'); end_date_str = request.form.get('constraint_end_date')
        if not start_date_str or not end_date_str:
            flash("Both start and end dates for unavailability are required.", "danger"); return redirect(target_redirect)
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if end_date_obj < start_date_obj:
            flash("End date cannot be before start date.", "danger"); return redirect(target_redirect)
        cs_dt = datetime.combine(start_date_obj, time.min); ce_dt = datetime.combine(end_date_obj, time.max)
        constraint = Constraint(worker_id=worker.id, constraint_type="UNAVAILABLE_DAY_RANGE", start_datetime=cs_dt, end_datetime=ce_dt)
        db.session.add(constraint); db.session.commit()
        flash(f'Unavailability added for {worker.name}.', 'success')
    except ValueError: flash("Invalid date format for unavailability.", "danger")
    except Exception as e:
        db.session.rollback(); flash(f'Error adding constraint: {e}', 'danger')
        current_app.logger.error(f"Error in add_constraint for worker {worker_id}: {e}\n{request.form}")
    return redirect(target_redirect)


@main_bp.route('/period/<int:period_id>/generate_slots_and_assign', methods=['POST'])
def generate_slots_and_assign_action(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    current_app.logger.info(f"Clearing old data for period {period.id} ('{period.name}')")
    ids_to_delete_assignments = [s.id for s in ScheduledShift.query.join(ShiftDefinition)
                               .filter(ShiftDefinition.scheduling_period_id == period_id).all()]
    if ids_to_delete_assignments:
        ScheduledShift.query.filter(ScheduledShift.id.in_(ids_to_delete_assignments)).delete(synchronize_session=False)
    ShiftDefinition.query.filter_by(scheduling_period_id=period.id).delete()
    db.session.commit()
    current_app.logger.info(f"Old data cleared for period {period.id}.")

    job_roles_for_period = JobRole.query.filter_by(scheduling_period_id=period.id).all()
    if not job_roles_for_period:
        flash("No job roles defined for this period. Cannot generate slots or assign.", "warning")
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    total_new_slots_generated = 0
    generated_slot_objects = []
    for role in job_roles_for_period:
        role_slots_generated_this_role = 0
        current_dt_for_role = period.period_start_datetime
        duration = role.get_duration_timedelta()
        if duration.total_seconds() <= 0:
            current_app.logger.warning(f"Skipping role '{role.name}' due to zero duration for period {period.id}.")
            flash(f"Job Role '{role.name}' has zero/negative shift duration and was skipped for slot generation.", "warning")
            continue
        max_iter = 5000; iter_count = 0
        while current_dt_for_role < period.period_end_datetime and iter_count < max_iter:
            iter_count += 1; slot_start = current_dt_for_role; slot_end = current_dt_for_role + duration
            if slot_end > period.period_end_datetime: slot_end = period.period_end_datetime
            if slot_start < slot_end:
                for i in range(1, role.number_needed + 1):
                    new_slot = ShiftDefinition(slot_start_datetime=slot_start, slot_end_datetime=slot_end,
                                               instance_number=i, scheduling_period_id=period.id, job_role_id=role.id)
                    db.session.add(new_slot); generated_slot_objects.append(new_slot); role_slots_generated_this_role +=1
            current_dt_for_role = slot_end
            if current_dt_for_role >= period.period_end_datetime: break
        if iter_count >= max_iter: flash(f"Max iterations for role '{role.name}' during slot generation.", "warning")
        total_new_slots_generated += role_slots_generated_this_role
    if total_new_slots_generated > 0:
        try:
            db.session.commit(); flash(f"{total_new_slots_generated} coverage slots generated for '{period.name}'. Attempting assignment...", "info")
            current_app.logger.info(f"{total_new_slots_generated} ShiftDefinition slots committed for period {period.id}.")
        except Exception as e:
            db.session.rollback(); flash(f"Error committing generated slots: {e}", "danger")
            current_app.logger.error(f"Error committing slots for period {period.id}: {e}")
            return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
    else:
        flash("No new coverage slots were generated. Check role durations. No assignments will be made.", "warning")
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    # --- Step 3: Prepare for and run assignment algorithm ---
    workers = Worker.query.options(selectinload(Worker.qualified_roles)).all()
    if not workers:
        flash("No workers found. Slots generated, but assignments cannot proceed.", "warning")
        # Store this message to be displayed on the next page, maybe in session for one request
        session['assignment_details'] = [("warning", "No workers found in the system to perform assignments.")]
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    assignments_to_make = []
    for slot_def in generated_slot_objects:
        if slot_def.id is None: continue
        assignments_to_make.append(ScheduledShift(shift_definition_id=slot_def.id))
    if assignments_to_make:
        db.session.add_all(assignments_to_make); db.session.commit()
        current_app.logger.info(f"{len(assignments_to_make)} ScheduledShift placeholders created for period {period.id}.")
    else:
        flash("No assignment placeholders created, though slots generated. Unexpected error.", "danger")
        current_app.logger.error(f"Failed to create ScheduledShift placeholders for period {period.id} despite {total_new_slots_generated} slots.")
        return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

    from .algorithm import assign_shifts_fairly
    all_pending_assignments = ScheduledShift.query.options(
            joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role)
        ).join(ShiftDefinition)\
        .filter(ShiftDefinition.scheduling_period_id == period.id, ScheduledShift.worker_id.is_(None))\
        .all()
    
    current_app.logger.info(f"Attempting to assign {len(all_pending_assignments)} slots for period {period.id}.")
    assignment_successful, algo_messages_raw = assign_shifts_fairly(all_pending_assignments, workers, period)
    
    # ---- MODIFIED MESSAGE HANDLING ----
    # Store detailed messages in session to be picked up by the next request (the redirect)
    # This is a common pattern for Post/Redirect/Get with complex feedback.
    detailed_assignment_warnings = []
    error_count = 0
    warning_summary_count = 0 # Count for summary message

    for msg_type, msg_text in algo_messages_raw:
        if msg_type == "error":
            error_count += 1
            current_app.logger.error(f"Algo Error: {msg_text}")
            # Flash critical errors immediately
            flash(f"Critical Algorithm Error: {msg_text}", "danger")
        elif msg_type == "warning": # Typically "Could not assign..."
            warning_summary_count +=1
            detailed_assignment_warnings.append(msg_text) # Collect for detailed display
            current_app.logger.warning(f"Algo Warning: {msg_text}")
        elif msg_type == "success":
            flash(msg_text, "success")
        else: # info or other types
            flash(msg_text, msg_type)
    
    session['assignment_details'] = detailed_assignment_warnings # Store details in session

    if error_count > 0:
        flash(f"{error_count} critical errors occurred during assignment. Check server logs.", "danger")
    
    if warning_summary_count > 0:
        flash(f"Assignment complete: {warning_summary_count} slots could not be filled. See details below or check server logs.", "warning")
    
    if assignment_successful and error_count == 0 and warning_summary_count == 0:
        flash("All shifts assigned successfully!", "success")
    elif not assignment_successful and error_count == 0 and warning_summary_count == 0:
        flash("Shift assignment process completed, but the algorithm reported not all shifts filled (no specific warnings).", "warning")
    elif total_new_slots_generated > 0 and not all_pending_assignments and (error_count > 0 or warning_summary_count > 0):
        flash("Slots were generated, but assignment step encountered issues before processing.", "danger")
    # A general info message isn't needed if specific summaries are given
    # ---- END OF MODIFIED MESSAGE HANDLING ----

    return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

# ... (manage_job_roles_for_period GET part needs to retrieve and pass these messages) ...