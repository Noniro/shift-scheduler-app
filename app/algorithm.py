from . import db
from .models import Worker, ScheduledShift, Constraint, ShiftDefinition, SchedulingPeriod, JobRole, WorkerRoleRating
from datetime import datetime, timedelta
from flask import config, current_app
from sqlalchemy.orm import joinedload
from collections import defaultdict

def is_worker_qualified_for_slot(worker: Worker, slot_def: ShiftDefinition):
    """Checks if a worker is qualified for the job role of a given shift slot."""
    if not slot_def.job_role:
        current_app.logger.error(f"Slot Definition {slot_def.id} has no associated JobRole.")
        return False
    
    worker_qualified_role_ids = {role.id for role in worker.qualified_roles}
    return slot_def.job_role_id in worker_qualified_role_ids


def is_worker_available_for_slot(worker: Worker, slot_def: ShiftDefinition):
    """
    Checks all of a worker's hard constraints:
    1. Role Qualification
    2. Unavailability periods (from worker constraints)
    """
    # 1. Check Role Qualification
    if not is_worker_qualified_for_slot(worker, slot_def):
        return False

    # 2. Check Unavailability Constraints
    for constraint in worker.constraints:
        # Check for any overlap between the shift and the constraint period
        if slot_def.slot_start_datetime < constraint.end_datetime and \
           slot_def.slot_end_datetime > constraint.start_datetime:
            return False
            
    return True


def get_recent_role_penalty(worker_id, role_id, slot_start, recent_assignments):
    """
    Calculate a penalty for assigning the same role to a worker on consecutive days.
    Returns a multiplier (1.0 = no penalty, higher = more penalty)
    """
    if worker_id not in recent_assignments:
        return 1.0
    
    slot_date = slot_start.date()
    
    # Check assignments from previous days
    for days_back in range(1, 4):  # Check up to 3 days back
        check_date = slot_date - timedelta(days=days_back)
        if check_date in recent_assignments[worker_id]:
            if role_id in recent_assignments[worker_id][check_date]:
                # Apply penalty that decreases with distance
                # Yesterday = 2.0x penalty, 2 days ago = 1.5x, 3 days ago = 1.2x
                penalty = 2.5 - (0.5 * days_back)
                return penalty
    
    return 1.0

# import random
# from collections import defaultdict

# # Update the assign_shifts_fairly function in algorithm.py
# def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
#     algo_messages = []
#     if not workers:
#         algo_messages.append(("error", "No workers available to assign shifts."))
#         return False, algo_messages
#     if not all_pending_assignments:
#         algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
#         return True, algo_messages

#     # Pre-fetch all slot definitions and their job roles for the pending assignments
#     slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
#     slot_definitions_map = {
#         sd.id: sd for sd in ShiftDefinition.query.options(
#             joinedload(ShiftDefinition.job_role)
#         ).filter(ShiftDefinition.id.in_(slot_ids)).all()
#     }

#     # Sort pending assignments by their underlying slot's start time
#     def get_start_time(assign_obj):
#         sd = slot_definitions_map.get(assign_obj.shift_definition_id)
#         return sd.slot_start_datetime if sd else datetime.max
#     all_pending_assignments.sort(key=get_start_time)

#     # Initialize tracking dictionaries
#     worker_assigned_hours_in_period = {w.id: 0.0 for w in workers}
#     worker_weighted_hours = {w.id: 0.0 for w in workers}
#     worker_shift_assignments_in_run = {w.id: [] for w in workers}
    
#     # Track recent role assignments by worker and date
#     recent_role_assignments = defaultdict(lambda: defaultdict(set))
    
#     unassigned_count = 0

#     for assignment_obj in all_pending_assignments:
#         slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
#         if not slot_def:
#             current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
#             algo_messages.append(("warning", f"Could not process a shift because its definition was missing. Please regenerate slots."))
#             unassigned_count += 1
#             continue

#         assigned_this_slot = False
#         slot_date = slot_def.slot_start_datetime.date()
#         role_id = slot_def.job_role_id
        
#         # Calculate real duration and multiplier
#         real_duration_hours = slot_def.duration_total_seconds / 3600.0
#         base_multiplier = slot_def.job_role.difficulty_multiplier
        
#         # Create a list of eligible workers with their effective scores
#         eligible_workers = []
        
#         for worker in workers:
#             # 1. Check hard constraints (availability, qualification)
#             if not is_worker_available_for_slot(worker, slot_def):
#                 continue

#             # 2. Check for overlapping shifts assigned in this algorithm run
#             is_overlapping = False
#             for other_assigned_slot in worker_shift_assignments_in_run[worker.id]:
#                 if max(slot_def.slot_start_datetime, other_assigned_slot.slot_start_datetime) < \
#                    min(slot_def.slot_end_datetime, other_assigned_slot.slot_end_datetime):
#                     is_overlapping = True
#                     break
#             if is_overlapping:
#                 continue
            
#             # 3. Check max hours constraint using REAL hours
#             if worker.max_hours_per_week:
#                 if (worker_assigned_hours_in_period[worker.id] + real_duration_hours) > worker.max_hours_per_week:
#                     continue
            
#             # Calculate effective weighted hours including role rotation penalty
#             role_penalty = get_recent_role_penalty(worker.id, role_id, slot_def.slot_start_datetime, recent_role_assignments)
#             effective_weighted_hours = worker_weighted_hours[worker.id] * role_penalty
            
#             eligible_workers.append((worker, effective_weighted_hours))
        
#         # ============ NEW: RANDOMIZED SORTING WITH TIE-BREAKING ============
#         # Sort eligible workers by their effective weighted hours, with random tie-breaking
#         eligible_workers.sort(key=lambda x: (x[1], random.random()))
#         # ============ END RANDOMIZED SORTING ============
        
#         # Try to assign to the worker with lowest effective weighted hours
#         for worker, _ in eligible_workers:
#             # Assign the shift
#             assignment_obj.worker_id = worker.id
            
#             # Update REAL hours
#             worker_assigned_hours_in_period[worker.id] += real_duration_hours
            
#             # Update WEIGHTED hours
#             worker_weighted_hours[worker.id] += real_duration_hours * base_multiplier
            
#             # Record this assignment for overlap checking
#             worker_shift_assignments_in_run[worker.id].append(slot_def)
            
#             # Track the role assignment for this worker and date
#             recent_role_assignments[worker.id][slot_date].add(role_id)
            
#             assigned_this_slot = True
#             break

#         if not assigned_this_slot:
#             unassigned_count += 1
#             algo_messages.append(("warning", f"Could not assign worker to: {slot_def.name} starting {slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}"))
    
#     try:
#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Algorithm: Error committing assignments: {e}")
#         algo_messages.append(("error", f"Database error during assignment commit: {e}"))
#         return False, algo_messages

#     if unassigned_count > 0:
#         algo_messages.append(("info", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned for period '{active_period.name}'."))
#         return False, algo_messages
            
#     algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned for period '{active_period.name}'."))
#     return True, algo_messages



# For getting individual difficulty ratings

def get_worker_individual_difficulty(worker_id, job_role_id, alpha=0.5):
    """
    Get hybrid difficulty rating combining objective base and subjective individual rating.
    
    Args:
        worker_id: The worker's ID
        job_role_id: The job role's ID
        alpha: Weight for base multiplier (0-1). Default 0.5 = 50/50 split
               - alpha=0: Pure individual ratings (subjective only)
               - alpha=1: Pure base multiplier (objective only)
               - alpha=0.5: Balanced hybrid (RECOMMENDED)
    
    Returns:
        float: Hybrid difficulty rating
    """
    # Get the role's base (objective/consensus) difficulty
    role = JobRole.query.get(job_role_id)
    base_difficulty = role.difficulty_multiplier if role else 1.0
    
    # Get the worker's individual (subjective) rating
    individual_rating = WorkerRoleRating.query.filter_by(
        worker_id=worker_id,
        job_role_id=job_role_id
    ).first()
    
    if individual_rating:
        # Hybrid: Combine base and individual
        subjective_difficulty = individual_rating.difficulty_rating
        hybrid_difficulty = (alpha * base_difficulty) + ((1 - alpha) * subjective_difficulty)
        return hybrid_difficulty
    else:
        # No individual rating: Fall back to base difficulty
        return base_difficulty
    
# import random
# from collections import defaultdict

# # Update the assign_shifts_fairly function in algorithm.py
# def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
#     algo_messages = []
#     if not workers:
#         algo_messages.append(("error", "No workers available to assign shifts."))
#         return False, algo_messages
#     if not all_pending_assignments:
#         algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
#         return True, algo_messages

#     # Pre-fetch all slot definitions and their job roles for the pending assignments
#     slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
#     slot_definitions_map = {
#         sd.id: sd for sd in ShiftDefinition.query.options(
#             joinedload(ShiftDefinition.job_role)
#         ).filter(ShiftDefinition.id.in_(slot_ids)).all()
#     }

#     # Sort pending assignments by their underlying slot's start time
#     def get_start_time(assign_obj):
#         sd = slot_definitions_map.get(assign_obj.shift_definition_id)
#         return sd.slot_start_datetime if sd else datetime.max
#     all_pending_assignments.sort(key=get_start_time)

#     # Initialize tracking dictionaries
#     worker_assigned_hours_in_period = {w.id: 0.0 for w in workers}
#     worker_weighted_hours = {w.id: 0.0 for w in workers}
#     worker_shift_assignments_in_run = {w.id: [] for w in workers}
    
#     # Track recent role assignments by worker and date
#     recent_role_assignments = defaultdict(lambda: defaultdict(set))
    
#     unassigned_count = 0

#     for assignment_obj in all_pending_assignments:
#         slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
#         if not slot_def:
#             current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
#             algo_messages.append(("warning", f"Could not process a shift because its definition was missing. Please regenerate slots."))
#             unassigned_count += 1
#             continue

#         assigned_this_slot = False
#         slot_date = slot_def.slot_start_datetime.date()
#         role_id = slot_def.job_role_id
        
#         # Calculate real duration
#         real_duration_hours = slot_def.duration_total_seconds / 3600.0
#         # Note: We'll use individual worker difficulty ratings instead of base_multiplier
            
#         # Create a list of eligible workers with their effective scores
#         eligible_workers = []
        
#         for worker in workers:
#             # 1. Check hard constraints (availability, qualification)
#             if not is_worker_available_for_slot(worker, slot_def):
#                 continue

#             # 2. Check for overlapping shifts assigned in this algorithm run
#             is_overlapping = False
#             for other_assigned_slot in worker_shift_assignments_in_run[worker.id]:
#                 if max(slot_def.slot_start_datetime, other_assigned_slot.slot_start_datetime) < \
#                 min(slot_def.slot_end_datetime, other_assigned_slot.slot_end_datetime):
#                     is_overlapping = True
#                     break
#             if is_overlapping:
#                 continue
            
#             # 3. Check max hours constraint using REAL hours
#             if worker.max_hours_per_week:
#                 if (worker_assigned_hours_in_period[worker.id] + real_duration_hours) > worker.max_hours_per_week:
#                     continue
            
#             # Calculate effective weighted hours including role rotation penalty
#             role_penalty = get_recent_role_penalty(worker.id, role_id, slot_def.slot_start_datetime, recent_role_assignments)
#             effective_weighted_hours = worker_weighted_hours[worker.id] * role_penalty
            
#             eligible_workers.append((worker, effective_weighted_hours))

#         # ============ NEW: RANDOMIZED SORTING WITH TIE-BREAKING ============
        
#         # Sort eligible workers by their effective weighted hours, with random tie-breaking
#         eligible_workers.sort(key=lambda x: (x[1], random.random()))
#         # ============ END RANDOMIZED SORTING ============
        
#         # Try to assign to the worker with lowest effective weighted hours
#         for worker, _ in eligible_workers:
#             # Assign the shift
#             assignment_obj.worker_id = worker.id
            
#             # Update REAL hours
#             worker_assigned_hours_in_period[worker.id] += real_duration_hours


#             # The bigger change is here:
#             # *** KEY CHANGE: Use worker's INDIVIDUAL difficulty rating ***
#             worker_individual_difficulty = get_worker_individual_difficulty(worker.id, role_id, alpha=current_app.config['DIFFICULTY_ALPHA'])
#             worker_weighted_hours[worker.id] += real_duration_hours * worker_individual_difficulty
    
#             # Record this assignment for overlap checking
#             worker_shift_assignments_in_run[worker.id].append(slot_def)
            
#             # Track the role assignment for this worker and date
#             recent_role_assignments[worker.id][slot_date].add(role_id)
            
#             assigned_this_slot = True
#             break

#         if not assigned_this_slot:
#             unassigned_count += 1
#             algo_messages.append(("warning", f"Could not assign worker to: {slot_def.name} starting {slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}"))
    
#     try:
#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Algorithm: Error committing assignments: {e}")
#         algo_messages.append(("error", f"Database error during assignment commit: {e}"))
#         return False, algo_messages

#     if unassigned_count > 0:
#         algo_messages.append(("info", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned for period '{active_period.name}'."))
#         return False, algo_messages
            
#     algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned for period '{active_period.name}'."))
#     return True, algo_messages



import random
from collections import defaultdict
from datetime import datetime as dt

def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
    algo_messages = []
    algo_logs = []  # NEW: Detailed logs for viewing
    
    # Log algorithm start
    start_time = dt.now()
    algo_logs.append({
        'type': 'header',
        'message': f"=== ALGORITHM START ===",
        'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    algo_logs.append({
        'type': 'info',
        'message': f"Period: {active_period.name}",
        'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    algo_logs.append({
        'type': 'info',
        'message': f"Total workers available: {len(workers)}",
        'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    algo_logs.append({
        'type': 'info',
        'message': f"Total shifts to assign: {len(all_pending_assignments)}",
        'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    if not workers:
        algo_messages.append(("error", "No workers available to assign shifts."))
        algo_logs.append({
            'type': 'error',
            'message': "CRITICAL: No workers available to assign shifts",
            'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return False, algo_messages, algo_logs
        
    if not all_pending_assignments:
        algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
        algo_logs.append({
            'type': 'info',
            'message': "No shifts were pending assignment",
            'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return True, algo_messages, algo_logs

    # Pre-fetch all slot definitions and their job roles for the pending assignments
    slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
    slot_definitions_map = {
        sd.id: sd for sd in ShiftDefinition.query.options(
            joinedload(ShiftDefinition.job_role)
        ).filter(ShiftDefinition.id.in_(slot_ids)).all()
    }

    # Sort pending assignments by their underlying slot's start time
    def get_start_time(assign_obj):
        sd = slot_definitions_map.get(assign_obj.shift_definition_id)
        return sd.slot_start_datetime if sd else datetime.max
    all_pending_assignments.sort(key=get_start_time)

    # Initialize tracking dictionaries
    worker_assigned_hours_in_period = {w.id: 0.0 for w in workers}
    worker_weighted_hours = {w.id: 0.0 for w in workers}
    worker_shift_assignments_in_run = {w.id: [] for w in workers}
    
    # Track recent role assignments by worker and date
    recent_role_assignments = defaultdict(lambda: defaultdict(set))
    
    # Log worker initial states
    algo_logs.append({
        'type': 'header',
        'message': f"\n=== WORKER INITIAL STATES ===",
        'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    for worker in workers:
        qualified_roles = [role.name for role in worker.qualified_roles]
        algo_logs.append({
            'type': 'info',
            'message': f"Worker: {worker.name}",
            'details': {
                'max_hours': worker.max_hours_per_week,
                'qualified_roles': qualified_roles,
                'num_constraints': len(list(worker.constraints))
            },
            'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    unassigned_count = 0
    assigned_count = 0

    algo_logs.append({
        'type': 'header',
        'message': f"\n=== STARTING SHIFT ASSIGNMENTS ===",
        'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    for idx, assignment_obj in enumerate(all_pending_assignments, 1):
        slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
        if not slot_def:
            current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
            algo_messages.append(("warning", f"Could not process a shift because its definition was missing. Please regenerate slots."))
            algo_logs.append({
                'type': 'error',
                'message': f"Shift {idx}: Missing shift definition ID {assignment_obj.shift_definition_id}",
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            unassigned_count += 1
            continue

        assigned_this_slot = False
        slot_date = slot_def.slot_start_datetime.date()
        role_id = slot_def.job_role_id
        
        # Calculate real duration
        real_duration_hours = slot_def.duration_total_seconds / 3600.0
        
        # Log shift being processed
        algo_logs.append({
            'type': 'shift_start',
            'message': f"\n--- Shift {idx}/{len(all_pending_assignments)}: {slot_def.name} ---",
            'details': {
                'start': slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M'),
                'end': slot_def.slot_end_datetime.strftime('%Y-%m-%d %H:%M'),
                'duration': f"{real_duration_hours:.2f}h",
                'role': slot_def.job_role.name
            },
            'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
            
        # Create a list of eligible workers with their effective scores
        eligible_workers = []
        rejection_reasons = defaultdict(list)
        
        for worker in workers:
            # 1. Check hard constraints (availability, qualification)
            if not is_worker_available_for_slot(worker, slot_def):
                if not is_worker_qualified_for_slot(worker, slot_def):
                    rejection_reasons[worker.name].append("Not qualified for role")
                else:
                    rejection_reasons[worker.name].append("Unavailable (constraint conflict)")
                continue

            # 2. Check for overlapping shifts assigned in this algorithm run
            is_overlapping = False
            for other_assigned_slot in worker_shift_assignments_in_run[worker.id]:
                if max(slot_def.slot_start_datetime, other_assigned_slot.slot_start_datetime) < \
                   min(slot_def.slot_end_datetime, other_assigned_slot.slot_end_datetime):
                    is_overlapping = True
                    rejection_reasons[worker.name].append(f"Overlaps with {other_assigned_slot.name}")
                    break
            if is_overlapping:
                continue
            
            # 3. Check max hours constraint using REAL hours
            if worker.max_hours_per_week:
                if (worker_assigned_hours_in_period[worker.id] + real_duration_hours) > worker.max_hours_per_week:
                    rejection_reasons[worker.name].append(f"Would exceed max hours ({worker.max_hours_per_week}h)")
                    continue
            
            # Calculate effective weighted hours including role rotation penalty
            role_penalty = get_recent_role_penalty(worker.id, role_id, slot_def.slot_start_datetime, recent_role_assignments)
            effective_weighted_hours = worker_weighted_hours[worker.id] * role_penalty
            
            eligible_workers.append((worker, effective_weighted_hours))
        
        # Log eligible workers
        if eligible_workers:
            algo_logs.append({
                'type': 'eligible',
                'message': f"  ✓ {len(eligible_workers)} eligible workers found",
                'details': {
                    'workers': [
                        {
                            'name': w.name,
                            'weighted_hours': f"{wh:.2f}h",
                            'real_hours': f"{worker_assigned_hours_in_period[w.id]:.2f}h"
                        } for w, wh in sorted(eligible_workers, key=lambda x: x[1])[:5]  # Top 5
                    ]
                },
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            algo_logs.append({
                'type': 'warning',
                'message': f"  ✗ NO eligible workers found",
                'details': {'rejections': dict(rejection_reasons)},
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Sort by effective weighted hours (lowest first)
        eligible_workers.sort(key=lambda x: (x[1], random.random()))
        
        # Try to assign to the worker with lowest effective weighted hours
        for worker, _ in eligible_workers:
            # Assign the shift
            assignment_obj.worker_id = worker.id
            
            # Update REAL hours
            worker_assigned_hours_in_period[worker.id] += real_duration_hours
            
            # Get worker's individual difficulty for this role
            worker_individual_difficulty = get_worker_individual_difficulty(worker.id, role_id, alpha=current_app.config['DIFFICULTY_ALPHA'])
            worker_weighted_hours[worker.id] += real_duration_hours * worker_individual_difficulty
            
            # Record this assignment for overlap checking
            worker_shift_assignments_in_run[worker.id].append(slot_def)
            
            # Track the role assignment for this worker and date
            recent_role_assignments[worker.id][slot_date].add(role_id)
            
            algo_logs.append({
                'type': 'success',
                'message': f"  ✓ ASSIGNED to {worker.name}",
                'details': {
                    'worker': worker.name,
                    'new_real_hours': f"{worker_assigned_hours_in_period[worker.id]:.2f}h",
                    'new_weighted_hours': f"{worker_weighted_hours[worker.id]:.2f}h",
                    'individual_difficulty': f"{worker_individual_difficulty:.2f}",
                    'total_shifts': len(worker_shift_assignments_in_run[worker.id])
                },
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            assigned_this_slot = True
            assigned_count += 1
            break

        if not assigned_this_slot:
            unassigned_count += 1
            algo_messages.append(("warning", f"Could not assign worker to: {slot_def.name} starting {slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}"))
            algo_logs.append({
                'type': 'error',
                'message': f"  ✗ UNASSIGNED - Could not find suitable worker",
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # Log final statistics
    algo_logs.append({
        'type': 'header',
        'message': f"\n=== ALGORITHM COMPLETE ===",
        'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    algo_logs.append({
        'type': 'summary',
        'message': f"Total shifts processed: {len(all_pending_assignments)}",
        'details': {
            'assigned': assigned_count,
            'unassigned': unassigned_count,
            'success_rate': f"{(assigned_count/len(all_pending_assignments)*100):.1f}%" if all_pending_assignments else "N/A"
        },
        'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Log final worker states
    algo_logs.append({
        'type': 'header',
        'message': f"\n=== FINAL WORKER STATES ===",
        'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    for worker in workers:
        if worker_assigned_hours_in_period[worker.id] > 0:
            algo_logs.append({
                'type': 'worker_final',
                'message': f"{worker.name}",
                'details': {
                    'real_hours': f"{worker_assigned_hours_in_period[worker.id]:.2f}h",
                    'weighted_hours': f"{worker_weighted_hours[worker.id]:.2f}h",
                    'shifts_assigned': len(worker_shift_assignments_in_run[worker.id]),
                    'max_hours': worker.max_hours_per_week or 'unlimited'
                },
                'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    end_time = dt.now()
    duration = (end_time - start_time).total_seconds()
    algo_logs.append({
        'type': 'footer',
        'message': f"\nExecution time: {duration:.2f} seconds",
        'timestamp': end_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Algorithm: Error committing assignments: {e}")
        algo_messages.append(("error", f"Database error during assignment commit: {e}"))
        algo_logs.append({
            'type': 'error',
            'message': f"DATABASE ERROR: {str(e)}",
            'timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return False, algo_messages, algo_logs

    if unassigned_count > 0:
        algo_messages.append(("info", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned for period '{active_period.name}'."))
        return False, algo_messages, algo_logs
            
    algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned for period '{active_period.name}'."))
    return True, algo_messages, algo_logs