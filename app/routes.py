from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app, session, make_response
from . import db
from .models import SchedulingPeriod, JobRole, ShiftDefinition, Worker, Constraint, ScheduledShift, User
from datetime import datetime, time, timedelta, date
from dateutil.parser import parse as parse_datetime
from sqlalchemy.orm import joinedload, selectinload # For eager loading

# For CSV export
import csv
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

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


    # Adding time restriction for job roles
def is_time_within_role_restrictions(check_time, role):
    """Check if a given time falls within the role's working hours"""
    if not role.has_time_restrictions():
        return True  # No restrictions means all times are valid
    
    check_time_only = check_time.time()
    
    if role.is_overnight_shift:
        # For overnight shifts (e.g., 22:00 - 06:00)
        # Valid if time >= start_time OR time <= end_time
        return check_time_only >= role.work_start_time or check_time_only <= role.work_end_time
    else:
        # For same-day shifts (e.g., 09:00 - 17:00)
        # Valid if start_time <= time <= end_time
        return role.work_start_time <= check_time_only <= role.work_end_time

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
    worker_hours = {} # NEW: Initialize worker hours dictionary

    if active_period:
        has_defined_shift_slots = ShiftDefinition.query.filter_by(scheduling_period_id=active_period.id).first() is not None
        if has_defined_shift_slots:
            scheduled_assignments = ScheduledShift.query.options(
                    joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role), # Eager load job_role
                    joinedload(ScheduledShift.worker_assigned)
                ).join(ShiftDefinition).\
                filter(ShiftDefinition.scheduling_period_id == active_period.id).\
                order_by(ShiftDefinition.slot_start_datetime, ShiftDefinition.job_role_id, ShiftDefinition.instance_number).all()

            # NEW: Calculate worker hours from assignments
            if scheduled_assignments:
                for assignment in scheduled_assignments:
                    if assignment.worker_assigned:
                        worker = assignment.worker_assigned
                        # Calculate duration in hours
                        duration_hours = assignment.defined_slot.duration_timedelta.total_seconds() / 3600.0
                        worker_hours[worker.name] = worker_hours.get(worker.name, 0) + duration_hours


    return render_template('index.html',
                           current_user_name=current_user_name,
                           active_period=active_period,
                           workers=workers,
                           scheduled_assignments=scheduled_assignments,
                           has_defined_shift_slots=has_defined_shift_slots,
                           worker_hours=worker_hours) # NEW: Pass data to template

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
    
    # Update your job role creation logic in routes.py
    # Find the manage_job_roles_for_period POST section and replace it with this:

    # if request.method == 'POST':
    #     try:
    #         role_name = request.form.get('role_name')
    #         number_needed_str = request.form.get('number_needed', '1')
    #         days_str = request.form.get('duration_days', '0')
    #         hours_str = request.form.get('duration_hours', '0')
    #         minutes_str = request.form.get('duration_minutes', '0')
            
    #         # GET the new multiplier value
    #         difficulty_multiplier_str = request.form.get('difficulty_multiplier', '1.0')

    #         # Time constraint fields
    #         has_time_restrictions = request.form.get('has_time_restrictions') == 'on'
    #         work_start_time_str = request.form.get('work_start_time')
    #         work_end_time_str = request.form.get('work_end_time')
    #         is_overnight_shift = request.form.get('is_overnight_shift') == 'on'
            
    #         if not role_name or not role_name.strip(): 
    #             flash("Job role name is required.", "danger")
    #         else:
    #             role_name = role_name.strip()
    #             number_needed = int(number_needed_str)
    #             days = int(days_str)
    #             hours = int(hours_str) 
    #             minutes = int(minutes_str)

    #             # CONVERT multiplier to float
    #             difficulty_multiplier = float(difficulty_multiplier_str)
                
    #             if number_needed < 1: 
    #                 flash("Number needed must be at least 1.", "danger")
    #             else:
    #                 total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
    #                 if total_duration_minutes < 20: 
    #                     flash("Minimum shift duration for a role is 20 minutes.", "danger")
    #                 elif days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60: 
    #                     flash("Invalid duration values (e.g., hours 0-23, minutes 0-59).", "danger")
    #                 elif JobRole.query.filter_by(scheduling_period_id=period.id, name=role_name).first(): 
    #                     flash(f"Job role '{role_name}' already exists for this period.", "warning")
    #                 else:
    #                     # Parse time constraints if provided
    #                     work_start_time = None
    #                     work_end_time = None
                        
    #                     if has_time_restrictions:
    #                         if not work_start_time_str or not work_end_time_str:
    #                             flash("Both start and end times are required when restricting working hours.", "danger")
    #                             return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                            
    #                         try:
    #                             work_start_time = datetime.strptime(work_start_time_str, '%H:%M').time()
    #                             work_end_time = datetime.strptime(work_end_time_str, '%H:%M').time()
                                
    #                             # Validate time logic
    #                             if not is_overnight_shift and work_end_time <= work_start_time:
    #                                 flash("End time must be after start time for same-day shifts.", "danger")
    #                                 return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
    #                             elif is_overnight_shift and work_end_time >= work_start_time:
    #                                 flash("For overnight shifts, end time should be earlier than start time (next day).", "warning")
                                    
    #                         except ValueError:
    #                             flash("Invalid time format. Please use HH:MM format.", "danger")
    #                             return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                        
    #                     new_role = JobRole(
    #                         name=role_name, 
    #                         number_needed=number_needed, 
    #                         shift_duration_days=days, 
    #                         shift_duration_hours=hours, 
    #                         shift_duration_minutes=minutes,
    #                         difficulty_multiplier=difficulty_multiplier, # ADD to object creation
    #                         scheduling_period_id=period.id,
    #                         work_start_time=work_start_time,
    #                         work_end_time=work_end_time,
    #                         is_overnight_shift=is_overnight_shift
    #                     )
    #                     db.session.add(new_role)
    #                     db.session.commit()
                        
    #                     time_info = ""
    #                     if has_time_restrictions:
    #                         time_info = f" (Working hours: {work_start_time_str} - {work_end_time_str}{'next day' if is_overnight_shift else ''})"
                        
    #                     flash(f"Job Role '{role_name}' added to period '{period.name}'.{time_info}", "success")
                        
    #     except ValueError: 
    #         flash("Invalid number for 'Needed' , 'Duration' or 'Multiplier' fields.", "danger")
    #     except Exception as e: 
    #         db.session.rollback()
    #         flash(f"Error adding job role: {e}", "danger")
    #         current_app.logger.error(f"Error adding job role for period {period.id}: {e}\n{request.form}")
    #     return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
    if request.method == 'POST':
        try:
            role_name = request.form.get('role_name')
            number_needed_str = request.form.get('number_needed', '1')
            days_str = request.form.get('duration_days', '0')
            hours_str = request.form.get('duration_hours', '0')
            minutes_str = request.form.get('duration_minutes', '0')
            
            # UPDATED: Handle the new 1-5 difficulty range
            difficulty_multiplier_str = request.form.get('difficulty_multiplier', '1')

            # Time constraint fields
            has_time_restrictions = request.form.get('has_time_restrictions') == 'on'
            work_start_time_str = request.form.get('work_start_time')
            work_end_time_str = request.form.get('work_end_time')
            is_overnight_shift = request.form.get('is_overnight_shift') == 'on'
            
            if not role_name or not role_name.strip(): 
                flash("Job role name is required.", "danger")
            else:
                role_name = role_name.strip()
                number_needed = int(number_needed_str)
                days = int(days_str)
                hours = int(hours_str) 
                minutes = int(minutes_str)

                # UPDATED: Convert multiplier to int and validate range 1-5
                difficulty_multiplier = int(difficulty_multiplier_str)
                if difficulty_multiplier < 1 or difficulty_multiplier > 5:
                    flash("Difficulty level must be between 1 and 5.", "danger")
                    return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                
                if number_needed < 1: 
                    flash("Number needed must be at least 1.", "danger")
                else:
                    total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
                    if total_duration_minutes < 20: 
                        flash("Minimum shift duration for a role is 20 minutes.", "danger")
                    elif days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60: 
                        flash("Invalid duration values (e.g., hours 0-23, minutes 0-59).", "danger")
                    elif JobRole.query.filter_by(scheduling_period_id=period.id, name=role_name).first(): 
                        flash(f"Job role '{role_name}' already exists for this period.", "warning")
                    else:
                        # Parse time constraints if provided
                        work_start_time = None
                        work_end_time = None
                        
                        if has_time_restrictions:
                            if not work_start_time_str or not work_end_time_str:
                                flash("Both start and end times are required when restricting working hours.", "danger")
                                return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                            
                            try:
                                work_start_time = datetime.strptime(work_start_time_str, '%H:%M').time()
                                work_end_time = datetime.strptime(work_end_time_str, '%H:%M').time()
                                
                                # Validate time logic
                                if not is_overnight_shift and work_end_time <= work_start_time:
                                    flash("End time must be after start time for same-day shifts.", "danger")
                                    return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                                elif is_overnight_shift and work_end_time >= work_start_time:
                                    flash("For overnight shifts, end time should be earlier than start time (next day).", "warning")
                                    
                            except ValueError:
                                flash("Invalid time format. Please use HH:MM format.", "danger")
                                return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
                        
                        new_role = JobRole(
                            name=role_name, 
                            number_needed=number_needed, 
                            shift_duration_days=days, 
                            shift_duration_hours=hours, 
                            shift_duration_minutes=minutes,
                            difficulty_multiplier=float(difficulty_multiplier), # Convert to float for database
                            scheduling_period_id=period.id,
                            work_start_time=work_start_time,
                            work_end_time=work_end_time,
                            is_overnight_shift=is_overnight_shift
                        )
                        db.session.add(new_role)
                        db.session.commit()
                        
                        time_info = ""
                        if has_time_restrictions:
                            time_info = f" (Working hours: {work_start_time_str} - {work_end_time_str}{'next day' if is_overnight_shift else ''})"
                        
                        difficulty_labels = {1: "Easy/Regular", 2: "Light", 3: "Moderate", 4: "Hard", 5: "Very Hard"}
                        flash(f"Job Role '{role_name}' added with difficulty level {difficulty_multiplier} ({difficulty_labels[difficulty_multiplier]}).{time_info}", "success")
                        
        except ValueError: 
            flash("Invalid number for 'Needed', 'Duration' or 'Difficulty' fields.", "danger")
        except Exception as e: 
            db.session.rollback()
            flash(f"Error adding job role: {e}", "danger")
            current_app.logger.error(f"Error adding job role for period {period.id}: {e}\n{request.form}")
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
                           workers_exist=workers_exist,
                           assignment_details=assignment_details) # Pass to template



@main_bp.route('/period/<int:period_id>/role/<int:role_id>/delete', methods=['POST'])
def delete_job_role(period_id, role_id):
    role = JobRole.query.filter_by(id=role_id, scheduling_period_id=period_id).first_or_404()
    db.session.delete(role); db.session.commit()
    flash(f"Job Role '{role.name}' and its generated slots/assignments deleted.", "info")
    return redirect(url_for('main.manage_job_roles_for_period', period_id=period_id))

# --- Job Role Editing Route ---
# This route allows editing an existing job role for a scheduling period.

@main_bp.route('/period/<int:period_id>/role/<int:role_id>/edit', methods=['GET', 'POST'])
def edit_job_role(period_id, role_id):
    """Edit an existing job role for a scheduling period"""
    period = SchedulingPeriod.query.get_or_404(period_id)
    role = JobRole.query.filter_by(id=role_id, scheduling_period_id=period_id).first_or_404()

    if request.method == 'POST':
        try:
            role_name = request.form.get('role_name')
            number_needed_str = request.form.get('number_needed', '1')
            days_str = request.form.get('duration_days', '0')
            hours_str = request.form.get('duration_hours', '0')
            minutes_str = request.form.get('duration_minutes', '0')
            
            # UPDATED: Handle the new 1-5 difficulty range
            difficulty_multiplier_str = request.form.get('difficulty_multiplier', '1')

            has_time_restrictions = request.form.get('has_time_restrictions') == 'on'
            work_start_time_str = request.form.get('work_start_time')
            work_end_time_str = request.form.get('work_end_time')
            is_overnight_shift = request.form.get('is_overnight_shift') == 'on'

            if not role_name or not role_name.strip():
                flash("Job role name is required.", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            role_name = role_name.strip()
            number_needed = int(number_needed_str)
            days = int(days_str)
            hours = int(hours_str)
            minutes = int(minutes_str)
            
            # UPDATED: Convert multiplier to int and validate range 1-5
            difficulty_multiplier = int(difficulty_multiplier_str)
            if difficulty_multiplier < 1 or difficulty_multiplier > 5:
                flash("Difficulty level must be between 1 and 5.", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            if number_needed < 1:
                flash("Number needed must be at least 1.", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
            if total_duration_minutes < 20:
                flash("Minimum shift duration for a role is 20 minutes.", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
            if days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60:
                flash("Invalid duration values (e.g., hours 0-23, minutes 0-59).", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            # Check if another role with same name exists in this period
            existing_role = JobRole.query.filter(
                JobRole.scheduling_period_id == period_id,
                JobRole.name.ilike(role_name),
                JobRole.id != role_id
            ).first()
            if existing_role:
                flash(f"Job role '{role_name}' already exists for this period.", "danger")
                return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            work_start_time = None
            work_end_time = None
            if has_time_restrictions:
                if not work_start_time_str or not work_end_time_str:
                    flash("Both start and end times are required when restricting working hours.", "danger")
                    return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
                try:
                    work_start_time = datetime.strptime(work_start_time_str, '%H:%M').time()
                    work_end_time = datetime.strptime(work_end_time_str, '%H:%M').time()
                    if not is_overnight_shift and work_end_time <= work_start_time:
                        flash("End time must be after start time for same-day shifts.", "danger")
                        return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
                    elif is_overnight_shift and work_end_time >= work_start_time:
                        flash("For overnight shifts, end time should be earlier than start time (next day).", "warning")
                except ValueError:
                    flash("Invalid time format. Please use HH:MM format.", "danger")
                    return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

            # Update role
            role.name = role_name
            role.number_needed = number_needed
            role.shift_duration_days = days
            role.shift_duration_hours = hours
            role.shift_duration_minutes = minutes
            role.difficulty_multiplier = float(difficulty_multiplier)  # Convert to float for database
            role.work_start_time = work_start_time
            role.work_end_time = work_end_time
            role.is_overnight_shift = is_overnight_shift if has_time_restrictions else False

            db.session.commit()
            
            difficulty_labels = {1: "Easy/Regular", 2: "Light", 3: "Moderate", 4: "Hard", 5: "Very Hard"}
            flash(f"Job Role '{role.name}' updated with difficulty level {difficulty_multiplier} ({difficulty_labels[difficulty_multiplier]}).", "success")
            return redirect(url_for('main.manage_job_roles_for_period', period_id=period_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating job role: {e}", "danger")
            current_app.logger.error(f"Error updating job role {role_id} for period {period_id}: {e}\n{request.form}")
            return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

    # GET request
    return render_template('edit_job_role.html', period=period, role=role)

# @main_bp.route('/period/<int:period_id>/role/<int:role_id>/edit', methods=['GET', 'POST'])
# def edit_job_role(period_id, role_id):
#     """Edit an existing job role for a scheduling period"""
#     period = SchedulingPeriod.query.get_or_404(period_id)
#     role = JobRole.query.filter_by(id=role_id, scheduling_period_id=period_id).first_or_404()

#     if request.method == 'POST':
#         try:
#             role_name = request.form.get('role_name')
#             number_needed_str = request.form.get('number_needed', '1')
#             days_str = request.form.get('duration_days', '0')
#             hours_str = request.form.get('duration_hours', '0')
#             minutes_str = request.form.get('duration_minutes', '0')

#             has_time_restrictions = request.form.get('has_time_restrictions') == 'on'
#             work_start_time_str = request.form.get('work_start_time')
#             work_end_time_str = request.form.get('work_end_time')
#             is_overnight_shift = request.form.get('is_overnight_shift') == 'on'

#             if not role_name or not role_name.strip():
#                 flash("Job role name is required.", "danger")
#                 return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#             role_name = role_name.strip()
#             number_needed = int(number_needed_str)
#             days = int(days_str)
#             hours = int(hours_str)
#             minutes = int(minutes_str)

#             if number_needed < 1:
#                 flash("Number needed must be at least 1.", "danger")
#                 return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#             total_duration_minutes = (days * 24 * 60) + (hours * 60) + minutes
#             if total_duration_minutes < 20:
#                 flash("Minimum shift duration for a role is 20 minutes.", "danger")
#                 return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
#             if days < 0 or hours < 0 or minutes < 0 or hours >= 24 or minutes >= 60:
#                 flash("Invalid duration values (e.g., hours 0-23, minutes 0-59).", "danger")
#                 return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#             # Check if another role with same name exists in this period
#             existing_role = JobRole.query.filter(
#                 JobRole.scheduling_period_id == period_id,
#                 JobRole.name.ilike(role_name),
#                 JobRole.id != role_id
#             ).first()
#             if existing_role:
#                 flash(f"Job role '{role_name}' already exists for this period.", "danger")
#                 return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#             work_start_time = None
#             work_end_time = None
#             if has_time_restrictions:
#                 if not work_start_time_str or not work_end_time_str:
#                     flash("Both start and end times are required when restricting working hours.", "danger")
#                     return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
#                 try:
#                     work_start_time = datetime.strptime(work_start_time_str, '%H:%M').time()
#                     work_end_time = datetime.strptime(work_end_time_str, '%H:%M').time()
#                     if not is_overnight_shift and work_end_time <= work_start_time:
#                         flash("End time must be after start time for same-day shifts.", "danger")
#                         return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))
#                     elif is_overnight_shift and work_end_time >= work_start_time:
#                         flash("For overnight shifts, end time should be earlier than start time (next day).", "warning")
#                 except ValueError:
#                     flash("Invalid time format. Please use HH:MM format.", "danger")
#                     return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#             # Update role
#             role.name = role_name
#             role.number_needed = number_needed
#             role.shift_duration_days = days
#             role.shift_duration_hours = hours
#             role.shift_duration_minutes = minutes
#             role.work_start_time = work_start_time
#             role.work_end_time = work_end_time
#             role.is_overnight_shift = is_overnight_shift if has_time_restrictions else False

#             db.session.commit()
#             flash(f"Job Role '{role.name}' updated.", "success")
#             return redirect(url_for('main.manage_job_roles_for_period', period_id=period_id))

#         except Exception as e:
#             db.session.rollback()
#             flash(f"Error updating job role: {e}", "danger")
#             current_app.logger.error(f"Error updating job role {role_id} for period {period_id}: {e}\n{request.form}")
#             return redirect(url_for('main.edit_job_role', period_id=period_id, role_id=role_id))

#     # GET request
#     return render_template('edit_job_role.html', period=period, role=role)

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


# Replace your add_constraint route in routes.py with this updated version:

@main_bp.route('/worker/<int:worker_id>/add_constraint', methods=['POST'])
def add_constraint(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    target_redirect = request.form.get('redirect_to', url_for('main.manage_workers'))
    
    try:
        constraint_type = request.form.get('constraint_type')  # 'full_day' or 'specific_hours'
        description = request.form.get('constraint_description', '').strip() or None
        
        if constraint_type == 'full_day':
            # Handle full day constraints (existing logic)
            start_date_str = request.form.get('constraint_start_date')
            end_date_str = request.form.get('constraint_end_date')
            
            if not start_date_str or not end_date_str:
                flash("Both start and end dates for unavailability are required.", "danger")
                return redirect(target_redirect)
                
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if end_date_obj < start_date_obj:
                flash("End date cannot be before start date.", "danger")
                return redirect(target_redirect)
                
            # Set to full day (00:00 to 23:59)
            cs_dt = datetime.combine(start_date_obj, time.min)
            ce_dt = datetime.combine(end_date_obj, time.max)
            constraint_type_db = "UNAVAILABLE_DAY_RANGE"
            
        elif constraint_type == 'specific_hours':
            # Handle specific hours constraints (new functionality)
            start_date_str = request.form.get('start_datetime_date')
            start_time_str = request.form.get('start_datetime_time')
            end_date_str = request.form.get('end_datetime_date')
            end_time_str = request.form.get('end_datetime_time')
            
            if not all([start_date_str, start_time_str, end_date_str, end_time_str]):
                flash("All date and time fields are required for specific hours constraints.", "danger")
                return redirect(target_redirect)
                
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
            
            cs_dt = datetime.combine(start_date_obj, start_time_obj)
            ce_dt = datetime.combine(end_date_obj, end_time_obj)
            
            if ce_dt <= cs_dt:
                flash("End date/time must be after start date/time.", "danger")
                return redirect(target_redirect)
                
            constraint_type_db = "UNAVAILABLE_TIME_RANGE"
            
        else:
            flash("Invalid constraint type.", "danger")
            return redirect(target_redirect)
        
        # Create the constraint
        constraint = Constraint(
            worker_id=worker.id, 
            constraint_type=constraint_type_db, 
            start_datetime=cs_dt, 
            end_datetime=ce_dt,
            description=description
        )
        
        db.session.add(constraint)
        db.session.commit()
        
        # Create success message
        duration_info = constraint.get_duration_str()
        constraint_desc = constraint.get_constraint_description()
        flash(f'Constraint added for {worker.name}: {constraint_desc} ({duration_info})', 'success')
        
    except ValueError as ve:
        flash(f"Invalid date/time format: {ve}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding constraint: {e}', 'danger')
        current_app.logger.error(f"Error in add_constraint for worker {worker_id}: {e}\n{request.form}")
    
    return redirect(target_redirect)

# Add this new route for deleting constraints:
@main_bp.route('/constraint/<int:constraint_id>/delete', methods=['POST'])
def delete_constraint(constraint_id):
    constraint = Constraint.query.get_or_404(constraint_id)
    worker_name = constraint.worker.name
    constraint_desc = constraint.get_constraint_description()
    
    db.session.delete(constraint)
    db.session.commit()
    
    flash(f'Constraint deleted for {worker_name}: {constraint_desc}', 'info')
    return redirect(url_for('main.manage_workers'))

# @main_bp.route('/worker/<int:worker_id>/add_constraint', methods=['POST'])
# def add_constraint(worker_id):
#     worker = Worker.query.get_or_404(worker_id)
#     target_redirect = request.form.get('redirect_to', url_for('main.manage_workers'))
#     try:
#         start_date_str = request.form.get('constraint_start_date'); end_date_str = request.form.get('constraint_end_date')
#         if not start_date_str or not end_date_str:
#             flash("Both start and end dates for unavailability are required.", "danger"); return redirect(target_redirect)
#         start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
#         if end_date_obj < start_date_obj:
#             flash("End date cannot be before start date.", "danger"); return redirect(target_redirect)
#         cs_dt = datetime.combine(start_date_obj, time.min); ce_dt = datetime.combine(end_date_obj, time.max)
#         constraint = Constraint(worker_id=worker.id, constraint_type="UNAVAILABLE_DAY_RANGE", start_datetime=cs_dt, end_datetime=ce_dt)
#         db.session.add(constraint); db.session.commit()
#         flash(f'Unavailability added for {worker.name}.', 'success')
#     except ValueError: flash("Invalid date format for unavailability.", "danger")
#     except Exception as e:
#         db.session.rollback(); flash(f'Error adding constraint: {e}', 'danger')
#         current_app.logger.error(f"Error in add_constraint for worker {worker_id}: {e}\n{request.form}")
#     return redirect(target_redirect)


# @main_bp.route('/period/<int:period_id>/generate_slots_and_assign', methods=['POST'])
# def generate_slots_and_assign_action(period_id):
#     period = SchedulingPeriod.query.get_or_404(period_id)
#     current_app.logger.info(f"Clearing old data for period {period.id} ('{period.name}')")
#     ids_to_delete_assignments = [s.id for s in ScheduledShift.query.join(ShiftDefinition)
#                                .filter(ShiftDefinition.scheduling_period_id == period_id).all()]
#     if ids_to_delete_assignments:
#         ScheduledShift.query.filter(ScheduledShift.id.in_(ids_to_delete_assignments)).delete(synchronize_session=False)
#     ShiftDefinition.query.filter_by(scheduling_period_id=period.id).delete()
#     db.session.commit()
#     current_app.logger.info(f"Old data cleared for period {period.id}.")

#     job_roles_for_period = JobRole.query.filter_by(scheduling_period_id=period.id).all()
#     if not job_roles_for_period:
#         flash("No job roles defined for this period. Cannot generate slots or assign.", "warning")
#         return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

#     total_new_slots_generated = 0
#     generated_slot_objects = []
#     for role in job_roles_for_period:
#         role_slots_generated_this_role = 0
#         current_dt_for_role = period.period_start_datetime
#         duration = role.get_duration_timedelta()
#         if duration.total_seconds() <= 0:
#             current_app.logger.warning(f"Skipping role '{role.name}' due to zero duration for period {period.id}.")
#             flash(f"Job Role '{role.name}' has zero/negative shift duration and was skipped for slot generation.", "warning")
#             continue
#         max_iter = 5000; iter_count = 0
#         while current_dt_for_role < period.period_end_datetime and iter_count < max_iter:
#             iter_count += 1; slot_start = current_dt_for_role; slot_end = current_dt_for_role + duration
#             if slot_end > period.period_end_datetime: slot_end = period.period_end_datetime
#             if slot_start < slot_end:
#                 for i in range(1, role.number_needed + 1):
#                     new_slot = ShiftDefinition(slot_start_datetime=slot_start, slot_end_datetime=slot_end,
#                                                instance_number=i, scheduling_period_id=period.id, job_role_id=role.id)
#                     db.session.add(new_slot); generated_slot_objects.append(new_slot); role_slots_generated_this_role +=1
#             current_dt_for_role = slot_end
#             if current_dt_for_role >= period.period_end_datetime: break
#         if iter_count >= max_iter: flash(f"Max iterations for role '{role.name}' during slot generation.", "warning")
#         total_new_slots_generated += role_slots_generated_this_role
#     if total_new_slots_generated > 0:
#         try:
#             db.session.commit(); flash(f"{total_new_slots_generated} coverage slots generated for '{period.name}'. Attempting assignment...", "info")
#             current_app.logger.info(f"{total_new_slots_generated} ShiftDefinition slots committed for period {period.id}.")
#         except Exception as e:
#             db.session.rollback(); flash(f"Error committing generated slots: {e}", "danger")
#             current_app.logger.error(f"Error committing slots for period {period.id}: {e}")
#             return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))
#     else:
#         flash("No new coverage slots were generated. Check role durations. No assignments will be made.", "warning")
#         return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

#     # --- Step 3: Prepare for and run assignment algorithm ---
#     workers = Worker.query.options(selectinload(Worker.qualified_roles)).all()
#     if not workers:
#         flash("No workers found. Slots generated, but assignments cannot proceed.", "warning")
#         # Store this message to be displayed on the next page, maybe in session for one request
#         session['assignment_details'] = [("warning", "No workers found in the system to perform assignments.")]
#         return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

#     assignments_to_make = []
#     for slot_def in generated_slot_objects:
#         if slot_def.id is None: continue
#         assignments_to_make.append(ScheduledShift(shift_definition_id=slot_def.id))
#     if assignments_to_make:
#         db.session.add_all(assignments_to_make); db.session.commit()
#         current_app.logger.info(f"{len(assignments_to_make)} ScheduledShift placeholders created for period {period.id}.")
#     else:
#         flash("No assignment placeholders created, though slots generated. Unexpected error.", "danger")
#         current_app.logger.error(f"Failed to create ScheduledShift placeholders for period {period.id} despite {total_new_slots_generated} slots.")
#         return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

#     from .algorithm import assign_shifts_fairly
#     all_pending_assignments = ScheduledShift.query.options(
#             joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role)
#         ).join(ShiftDefinition)\
#         .filter(ShiftDefinition.scheduling_period_id == period.id, ScheduledShift.worker_id.is_(None))\
#         .all()
    
#     current_app.logger.info(f"Attempting to assign {len(all_pending_assignments)} slots for period {period.id}.")
#     assignment_successful, algo_messages_raw = assign_shifts_fairly(all_pending_assignments, workers, period)
    
#     # ---- MODIFIED MESSAGE HANDLING ----
#     # Store detailed messages in session to be picked up by the next request (the redirect)
#     # This is a common pattern for Post/Redirect/Get with complex feedback.
#     detailed_assignment_warnings = []
#     error_count = 0
#     warning_summary_count = 0 # Count for summary message

#     for msg_type, msg_text in algo_messages_raw:
#         if msg_type == "error":
#             error_count += 1
#             current_app.logger.error(f"Algo Error: {msg_text}")
#             # Flash critical errors immediately
#             flash(f"Critical Algorithm Error: {msg_text}", "danger")
#         elif msg_type == "warning": # Typically "Could not assign..."
#             warning_summary_count +=1
#             detailed_assignment_warnings.append(msg_text) # Collect for detailed display
#             current_app.logger.warning(f"Algo Warning: {msg_text}")
#         elif msg_type == "success":
#             flash(msg_text, "success")
#         else: # info or other types
#             flash(msg_text, msg_type)
    
#     session['assignment_details'] = detailed_assignment_warnings # Store details in session

#     if error_count > 0:
#         flash(f"{error_count} critical errors occurred during assignment. Check server logs.", "danger")
    
#     if warning_summary_count > 0:
#         flash(f"Assignment complete: {warning_summary_count} slots could not be filled. See details below or check server logs.", "warning")
    
#     if assignment_successful and error_count == 0 and warning_summary_count == 0:
#         flash("All shifts assigned successfully!", "success")
#     elif not assignment_successful and error_count == 0 and warning_summary_count == 0:
#         flash("Shift assignment process completed, but the algorithm reported not all shifts filled (no specific warnings).", "warning")
#     elif total_new_slots_generated > 0 and not all_pending_assignments and (error_count > 0 or warning_summary_count > 0):
#         flash("Slots were generated, but assignment step encountered issues before processing.", "danger")
#     # A general info message isn't needed if specific summaries are given
#     # ---- END OF MODIFIED MESSAGE HANDLING ----

#     return redirect(url_for('main.manage_job_roles_for_period', period_id=period.id))

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
            
        max_iter = 5000
        iter_count = 0
        
        while current_dt_for_role < period.period_end_datetime and iter_count < max_iter:
            iter_count += 1
            
            # Check if current time is within role's working hours
            if role.has_time_restrictions():
                if not is_time_within_role_restrictions(current_dt_for_role, role):
                    # Move to next valid time slot
                    if role.is_overnight_shift:
                        # For overnight shifts, find next start time
                        next_start = current_dt_for_role.replace(
                            hour=role.work_start_time.hour, 
                            minute=role.work_start_time.minute, 
                            second=0, 
                            microsecond=0
                        )
                        if next_start <= current_dt_for_role:
                            next_start += timedelta(days=1)
                        current_dt_for_role = next_start
                    else:
                        # For day shifts, find next start time
                        next_start = current_dt_for_role.replace(
                            hour=role.work_start_time.hour, 
                            minute=role.work_start_time.minute, 
                            second=0, 
                            microsecond=0
                        )
                        if next_start <= current_dt_for_role:
                            next_start += timedelta(days=1)
                        current_dt_for_role = next_start
                    continue
            
            slot_start = current_dt_for_role
            slot_end = current_dt_for_role + duration
            
            # For time-restricted roles, ensure slot doesn't exceed working hours
            if role.has_time_restrictions():
                if role.is_overnight_shift:
                    # For overnight shifts, check if slot end goes beyond end time (next day)
                    next_day_end = (slot_start.replace(
                        hour=role.work_end_time.hour, 
                        minute=role.work_end_time.minute, 
                        second=0, 
                        microsecond=0
                    ) + timedelta(days=1))
                    
                    if slot_end > next_day_end:
                        slot_end = next_day_end
                else:
                    # For day shifts, check if slot end goes beyond end time (same day)
                    same_day_end = slot_start.replace(
                        hour=role.work_end_time.hour, 
                        minute=role.work_end_time.minute, 
                        second=0, 
                        microsecond=0
                    )
                    
                    if slot_end > same_day_end:
                        slot_end = same_day_end
            
            # Ensure slot doesn't exceed period end
            if slot_end > period.period_end_datetime:
                slot_end = period.period_end_datetime
            
            if slot_start < slot_end:
                for i in range(1, role.number_needed + 1):
                    new_slot = ShiftDefinition(
                        slot_start_datetime=slot_start, 
                        slot_end_datetime=slot_end,
                        instance_number=i, 
                        scheduling_period_id=period.id, 
                        job_role_id=role.id
                    )
                    db.session.add(new_slot)
                    generated_slot_objects.append(new_slot)
                    role_slots_generated_this_role += 1
            
            # Move to next slot time
            current_dt_for_role = slot_end
            
            if current_dt_for_role >= period.period_end_datetime:
                break
                
        if iter_count >= max_iter: 
            flash(f"Max iterations for role '{role.name}' during slot generation.", "warning")
        
        total_new_slots_generated += role_slots_generated_this_role
        
        # Log information about what was generated
        if role.has_time_restrictions():
            current_app.logger.info(f"Generated {role_slots_generated_this_role} time-restricted slots for role '{role.name}' ({role.get_working_hours_str()})")
        else:
            current_app.logger.info(f"Generated {role_slots_generated_this_role} all-day slots for role '{role.name}'")
    
    if total_new_slots_generated > 0:
        try:
            db.session.commit()
            flash(f"{total_new_slots_generated} coverage slots generated for '{period.name}'. Attempting assignment...", "info")
            current_app.logger.info(f"{total_new_slots_generated} ShiftDefinition slots committed for period {period.id}.")
        except Exception as e:
            db.session.rollback()
            flash(f"Error committing generated slots: {e}", "danger")
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
        if slot_def.id is None: 
            continue
        assignments_to_make.append(ScheduledShift(shift_definition_id=slot_def.id))
    
    if assignments_to_make:
        db.session.add_all(assignments_to_make)
        db.session.commit()
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
            warning_summary_count += 1
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

# Add these new export routes at the end of your routes.py file, before the final comment
@main_bp.route('/period/<int:period_id>/export_schedule_csv')
def export_schedule_csv(period_id):
    """Export the schedule for a specific period as CSV"""
    period = SchedulingPeriod.query.get_or_404(period_id)
    
    # Get all scheduled assignments for this period
    scheduled_assignments = ScheduledShift.query.options(
        joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role),
        joinedload(ScheduledShift.worker_assigned)
    ).join(ShiftDefinition).\
    filter(ShiftDefinition.scheduling_period_id == period.id).\
    order_by(ShiftDefinition.slot_start_datetime, ShiftDefinition.job_role_id, ShiftDefinition.instance_number).all()
    
    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Role & Instance',
        'Start Date',
        'Start Time', 
        'End Date',
        'End Time',
        'Duration',
        'Assigned Worker',
        'Worker Email'
    ])
    
    # Write data rows
    for assignment in scheduled_assignments:
        slot = assignment.defined_slot
        worker = assignment.worker_assigned
        
        writer.writerow([
            slot.name,
            slot.slot_start_datetime.strftime('%Y-%m-%d'),
            slot.slot_start_datetime.strftime('%H:%M'),
            slot.slot_end_datetime.strftime('%Y-%m-%d'), 
            slot.slot_end_datetime.strftime('%H:%M'),
            slot.duration_hours_minutes_str,
            worker.name if worker else 'UNASSIGNED',
            worker.email if worker and worker.email else ''
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=schedule_{period.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

@main_bp.route('/period/<int:period_id>/export_schedule_excel')
def export_schedule_excel(period_id):
    """Export the schedule for a specific period as Excel"""
    period = SchedulingPeriod.query.get_or_404(period_id)
    
    # Get all scheduled assignments for this period
    scheduled_assignments = ScheduledShift.query.options(
        joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role),
        joinedload(ScheduledShift.worker_assigned)
    ).join(ShiftDefinition).\
    filter(ShiftDefinition.scheduling_period_id == period.id).\
    order_by(ShiftDefinition.slot_start_datetime, ShiftDefinition.job_role_id, ShiftDefinition.instance_number).all()
    
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    unassigned_fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add title
    ws.merge_cells('A1:H1')
    title_cell = ws['A1']
    title_cell.value = f"Schedule for {period.name}"
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal='center')
    
    # Add period info
    ws.merge_cells('A2:H2')
    period_cell = ws['A2']
    period_cell.value = f"Period: {period.period_start_datetime.strftime('%Y-%m-%d %H:%M')} to {period.period_end_datetime.strftime('%Y-%m-%d %H:%M')}"
    period_cell.alignment = Alignment(horizontal='center')
    
    # Add headers starting from row 4
    headers = [
        'Role & Instance',
        'Start Date',
        'Start Time',
        'End Date', 
        'End Time',
        'Duration',
        'Assigned Worker',
        'Worker Email'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    # Add data starting from row 5
    for row, assignment in enumerate(scheduled_assignments, 5):
        slot = assignment.defined_slot
        worker = assignment.worker_assigned
        
        data = [
            slot.name,
            slot.slot_start_datetime.strftime('%Y-%m-%d'),
            slot.slot_start_datetime.strftime('%H:%M'),
            slot.slot_end_datetime.strftime('%Y-%m-%d'),
            slot.slot_end_datetime.strftime('%H:%M'),
            slot.duration_hours_minutes_str,
            worker.name if worker else 'UNASSIGNED',
            worker.email if worker and worker.email else ''
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            
            # Highlight unassigned shifts
            if not worker and col <= 8:
                cell.fill = unassigned_fill
    
    # Auto-adjust column widths
    from openpyxl.utils import get_column_letter
    
    for col_num in range(1, 9):  # We have 8 columns (A to H)
        max_length = 0
        for row in ws.iter_rows(min_col=col_num, max_col=col_num):
            for cell in row:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
        adjusted_width = min(max_length + 2, 50)
        column_letter = get_column_letter(col_num)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Create response
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=schedule_{period.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return response


# Import the function here to avoid import issues
from .algorithm import is_worker_qualified_for_slot

# For editing time periods, you can add a route like this:
@main_bp.route('/period/<int:period_id>/edit', methods=['GET', 'POST'])
def edit_period(period_id):
    period = SchedulingPeriod.query.get_or_404(period_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('period_name')
            start_date_str = request.form.get('period_start_date_hidden')
            end_date_str = request.form.get('period_end_date_hidden')
            start_time_str = request.form.get('period_start_time')
            end_time_str = request.form.get('period_end_time')

            if not name or not name.strip():
                flash("Period name is required.", "danger")
                return redirect(url_for('main.edit_period', period_id=period_id))
            name = name.strip()

            if not all([start_date_str, end_date_str, start_time_str, end_time_str]):
                flash("All period date and time fields are required.", "danger")
                return redirect(url_for('main.edit_period', period_id=period_id))

            # Check if name is taken by another period (not this one)
            existing_period = SchedulingPeriod.query.filter(
                SchedulingPeriod.name.ilike(name),
                SchedulingPeriod.id != period_id
            ).first()
            if existing_period:
                flash(f"A scheduling period with the name '{name}' already exists.", "danger")
                return redirect(url_for('main.edit_period', period_id=period_id))

            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()

            if end_date_obj < start_date_obj or \
               (end_date_obj == start_date_obj and end_time_obj <= start_time_obj):
                flash("Period end must be after period start.", "danger")
                return redirect(url_for('main.edit_period', period_id=period_id))

            period_start_dt = datetime.combine(start_date_obj, start_time_obj)
            period_end_dt = datetime.combine(end_date_obj, end_time_obj)
            
            # Update the period
            period.name = name
            period.period_start_datetime = period_start_dt
            period.period_end_datetime = period_end_dt

            db.session.commit()
            flash(f"Scheduling Period '{name}' updated successfully.", "success")
            return redirect(url_for('main.manage_periods'))
            
        except ValueError as ve:
            flash(f"Invalid date or time format: {ve}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating period: {e}", "danger")
            current_app.logger.error(f"Error updating period {period_id}: {e}\n{request.form}")
        return redirect(url_for('main.edit_period', period_id=period_id))

    # GET request - show edit form
    return render_template('edit_period.html', period=period)


    # Option to edit the "Home\Dashboard" list manually if needed
    # Add these routes to your routes.py file for manual assignment editing

@main_bp.route('/assignment/<int:assignment_id>/edit_worker', methods=['POST'])
def edit_assignment_worker(assignment_id):
    """Manually assign or reassign a worker to a specific shift"""
    assignment = ScheduledShift.query.get_or_404(assignment_id)
    new_worker_id = request.form.get('worker_id')
    
    # Get the shift definition to check role requirements
    shift_def = assignment.defined_slot
    if not shift_def:
        flash("Error: Shift definition not found.", "danger")
        return redirect(url_for('main.index'))
    
    try:
        if new_worker_id == 'unassign':
            # Unassign the worker
            old_worker_name = assignment.worker_assigned.name if assignment.worker_assigned else "unassigned"
            assignment.worker_id = None
            db.session.commit()
            flash(f"Unassigned {old_worker_name} from {shift_def.name} on {shift_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}", "info")
            
        elif new_worker_id and new_worker_id.isdigit():
            # Assign to a specific worker
            new_worker = Worker.query.get(int(new_worker_id))
            if not new_worker:
                flash("Worker not found.", "danger")
                return redirect(url_for('main.index'))
            
            # Check if worker is qualified for this role
            if not is_worker_qualified_for_slot(new_worker, shift_def):
                flash(f"Warning: {new_worker.name} is not qualified for role {shift_def.job_role.name}, but assignment was made anyway.", "warning")
            
            # Check for conflicts with other assignments
            active_period = get_active_period()
            if active_period:
                # Get all other assignments for this worker in the same period
                conflicting_assignments = ScheduledShift.query.options(
                    joinedload(ScheduledShift.defined_slot)
                ).join(ShiftDefinition).filter(
                    ShiftDefinition.scheduling_period_id == active_period.id,
                    ScheduledShift.worker_id == new_worker.id,
                    ScheduledShift.id != assignment_id
                ).all()
                
                # Check for time overlaps
                for other_assignment in conflicting_assignments:
                    other_slot = other_assignment.defined_slot
                    if (max(shift_def.slot_start_datetime, other_slot.slot_start_datetime) < 
                        min(shift_def.slot_end_datetime, other_slot.slot_end_datetime)):
                        flash(f"Warning: Time conflict detected with {other_slot.name} on {other_slot.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}, but assignment was made anyway.", "warning")
                        break
            
            old_worker_name = assignment.worker_assigned.name if assignment.worker_assigned else "unassigned"
            assignment.worker_id = new_worker.id
            db.session.commit()
            
            if old_worker_name != "unassigned":
                flash(f"Reassigned {shift_def.name} from {old_worker_name} to {new_worker.name} on {shift_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}", "success")
            else:
                flash(f"Assigned {new_worker.name} to {shift_def.name} on {shift_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}", "success")
        else:
            flash("Invalid worker selection.", "danger")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating assignment: {e}", "danger")
        current_app.logger.error(f"Error in edit_assignment_worker for assignment {assignment_id}: {e}")
    
    return redirect(url_for('main.index'))

@main_bp.route('/assignment/<int:assignment_id>/swap', methods=['POST'])
def swap_assignments(assignment_id):
    """Swap workers between two assignments"""
    assignment1 = ScheduledShift.query.get_or_404(assignment_id)
    assignment2_id = request.form.get('swap_with_assignment_id')
    
    if not assignment2_id or not assignment2_id.isdigit():
        flash("Invalid assignment to swap with.", "danger")
        return redirect(url_for('main.index'))
    
    assignment2 = ScheduledShift.query.get(int(assignment2_id))
    if not assignment2:
        flash("Assignment to swap with not found.", "danger")
        return redirect(url_for('main.index'))
    
    try:
        # Get worker info before swap
        worker1 = assignment1.worker_assigned
        worker2 = assignment2.worker_assigned
        shift1 = assignment1.defined_slot
        shift2 = assignment2.defined_slot
        
        # Perform the swap
        assignment1.worker_id = worker2.id if worker2 else None
        assignment2.worker_id = worker1.id if worker1 else None
        
        db.session.commit()
        
        worker1_name = worker1.name if worker1 else "unassigned"
        worker2_name = worker2.name if worker2 else "unassigned"
        
        flash(f"Swapped assignments: {worker1_name} ↔ {worker2_name} between {shift1.name} and {shift2.name}", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error swapping assignments: {e}", "danger")
        current_app.logger.error(f"Error in swap_assignments: {e}")
    
    return redirect(url_for('main.index'))


    # Adding statistics page to know how many shifts were assigned, unassigned, how did shift at night, etc.
    # Also we want to see from each role how each worker performed, how many shifts were assigned to each worker, etc.

# The statistics route to display fairness and workload distribution
from collections import defaultdict

@main_bp.route('/period/<int:period_id>/fairness_statistics')
def fairness_statistics(period_id):
    """Display fairness and workload distribution statistics for a period."""
    period = SchedulingPeriod.query.get_or_404(period_id)
    all_workers = Worker.query.order_by(Worker.name).all()
    all_roles = JobRole.query.filter_by(scheduling_period_id=period.id).order_by(JobRole.name).all()

    if not all_workers:
        flash("No workers found to generate statistics.", "warning")
        return redirect(url_for('main.manage_workers'))

    # Eagerly load all necessary data
    all_assignments = ScheduledShift.query.options(
        joinedload(ScheduledShift.defined_slot).joinedload(ShiftDefinition.job_role),
        joinedload(ScheduledShift.worker_assigned)
    ).join(ShiftDefinition).filter(
        ShiftDefinition.scheduling_period_id == period.id
    ).all()

    # --- Initialize Statistics Dictionaries ---
    stats = {
        'total_shifts': len(all_assignments), 'assigned_shifts': 0, 'unassigned_shifts': 0,
        'unassigned_shifts_list': [], 'worker_stats': {}, 'role_stats': {}
    }
    period_duration_hours = (period.period_end_datetime - period.period_start_datetime).total_seconds() / 3600.0

    for worker in all_workers:
        stats['worker_stats'][worker.id] = {
            'name': worker.name, 'total_shifts': 0, 'total_hours': 0.0, 'night_shifts': 0,
            'weekend_shifts': 0, 'difficulty_counts': defaultdict(int),
            'downtime_hours': period_duration_hours, 'role_distribution': defaultdict(int)
        }
    for role in all_roles:
        stats['role_stats'][role.id] = {
            'name': role.name, 'total_shifts': 0, 'total_hours': 0.0,
            'worker_distribution': defaultdict(int), 'unique_workers': 0
        }

    # --- Process All Assignments ---
    NIGHT_START_TIME = time(0, 0)
    NIGHT_END_TIME = time(6, 0)

    for assignment in all_assignments:
        slot = assignment.defined_slot
        if not slot or not slot.job_role: continue
        role = slot.job_role
        stats['role_stats'][role.id]['total_shifts'] += 1
        stats['role_stats'][role.id]['total_hours'] += slot.duration_total_seconds / 3600.0

        if assignment.worker_assigned:
            stats['assigned_shifts'] += 1
            worker = assignment.worker_assigned
            worker_stat = stats['worker_stats'][worker.id]
            duration_hours = slot.duration_total_seconds / 3600.0
            
            worker_stat['total_shifts'] += 1
            worker_stat['total_hours'] += duration_hours
            worker_stat['downtime_hours'] -= duration_hours
            
            # Check for night shift
            if slot.slot_start_datetime.time() < NIGHT_END_TIME:
                worker_stat['night_shifts'] += 1
            
            # Check for weekend shift (Saturday is 5, Sunday is 6)
            if slot.slot_start_datetime.weekday() >= 5:
                worker_stat['weekend_shifts'] += 1

            # Difficulty & Role Distribution
            worker_stat['difficulty_counts'][int(role.difficulty_multiplier)] += 1
            worker_stat['role_distribution'][role.name] += 1
            stats['role_stats'][role.id]['worker_distribution'][worker.name] += 1

        else:
            stats['unassigned_shifts'] += 1
            stats['unassigned_shifts_list'].append(assignment)

    for role_stat in stats['role_stats'].values():
        role_stat['unique_workers'] = len(role_stat['worker_distribution'])

    # --- Generate Key Fairness Insights ---
    insights = []
    if stats['assigned_shifts'] > 0:
        active_workers = [w for w in stats['worker_stats'].values() if w['total_shifts'] > 0]
        if not active_workers: active_workers = stats['worker_stats'].values()
        
        avg_hours = sum(w['total_hours'] for w in active_workers) / len(active_workers)
        avg_night = sum(w['night_shifts'] for w in active_workers) / len(active_workers)
        avg_weekend = sum(w['weekend_shifts'] for w in active_workers) / len(active_workers)
        
        for w in stats['worker_stats'].values():
            if w['total_hours'] > avg_hours * 1.5:
                insights.append(f"<b>{w['name']}</b> is working significantly more hours ({w['total_hours']:.1f}) than the average ({avg_hours:.1f}).")
            if w['total_hours'] < avg_hours * 0.5 and w['total_shifts'] > 0:
                 insights.append(f"<b>{w['name']}</b> is working significantly fewer hours ({w['total_hours']:.1f}) than the average ({avg_hours:.1f}).")
            if avg_night > 0.5 and w['night_shifts'] > avg_night * 1.75:
                insights.append(f"<b>{w['name']}</b> has a high number of night shifts ({w['night_shifts']}).")
            if avg_weekend > 0.5 and w['weekend_shifts'] > avg_weekend * 1.75:
                 insights.append(f"<b>{w['name']}</b> has a high number of weekend shifts ({w['weekend_shifts']}).")
            if w['total_shifts'] == 0:
                insights.append(f"<b>{w['name']}</b> was not assigned any shifts.")
    if stats['unassigned_shifts'] > 0:
        insights.append(f"There are <b>{stats['unassigned_shifts']} unassigned shifts</b> that need coverage.")

    return render_template('fairness_statistics.html', period=period, stats=stats, insights=insights)