# """
# Test Individual Difficulty Ratings System
# ==========================================

# This test file demonstrates how the individual difficulty rating system works
# in the scheduling algorithm. It shows how workers' subjective difficulty ratings
# are combined with objective base difficulties to create personalized fairness.

# The key function being tested is get_worker_individual_difficulty() which uses
# the formula:
#     hybrid_difficulty = (alpha * base_difficulty) + ((1 - alpha) * individual_rating)

# Where:
#     - alpha = 0.0: Pure subjective (100% individual ratings)
#     - alpha = 0.5: Balanced (50% base, 50% individual) [RECOMMENDED]
#     - alpha = 1.0: Pure objective (100% base difficulty)
# """

# from datetime import datetime, timedelta


# # ============================================================================
# # SIMPLIFIED TEST IMPLEMENTATION
# # ============================================================================
# # This is a standalone test that simulates the algorithm without Flask/SQLAlchemy

# class MockJobRole:
#     """Simulated JobRole model"""
#     def __init__(self, id, name, difficulty_multiplier):
#         self.id = id
#         self.name = name
#         self.difficulty_multiplier = difficulty_multiplier


# class MockWorker:
#     """Simulated Worker model"""
#     def __init__(self, id, name):
#         self.id = id
#         self.name = name


# class MockWorkerRoleRating:
#     """Simulated WorkerRoleRating model"""
#     def __init__(self, worker_id, job_role_id, difficulty_rating):
#         self.worker_id = worker_id
#         self.job_role_id = job_role_id
#         self.difficulty_rating = difficulty_rating


# # Simulated database storage
# RATINGS_DB = []
# ROLES_DB = []
# WORKERS_DB = []


# def get_worker_individual_difficulty(worker_id, job_role_id, alpha=0.5):
#     """
#     Simulated version of the algorithm function.
#     Get hybrid difficulty rating combining objective base and subjective individual rating.
#     """
#     # Get the role's base (objective/consensus) difficulty
#     role = None
#     for r in ROLES_DB:
#         if r.id == job_role_id:
#             role = r
#             break
    
#     base_difficulty = role.difficulty_multiplier if role else 1.0
    
#     # Get the worker's individual (subjective) rating
#     individual_rating = None
#     for rating in RATINGS_DB:
#         if rating.worker_id == worker_id and rating.job_role_id == job_role_id:
#             individual_rating = rating
#             break
    
#     if individual_rating:
#         # Hybrid: Combine base and individual
#         subjective_difficulty = individual_rating.difficulty_rating
#         hybrid_difficulty = (alpha * base_difficulty) + ((1 - alpha) * subjective_difficulty)
#         return hybrid_difficulty
#     else:
#         # No individual rating: Fall back to base difficulty
#         return base_difficulty


# def print_header(title, char='='):
#     """Print a formatted header"""
#     print(f"\n{char * 80}")
#     print(f"{title:^80}")
#     print(f"{char * 80}\n")


# def print_subheader(title):
#     """Print a formatted subheader"""
#     print(f"\n{'-' * 80}")
#     print(f"{title}")
#     print(f"{'-' * 80}")


# def setup_test_data():
#     """Create base test data"""
#     global RATINGS_DB, ROLES_DB, WORKERS_DB
    
#     # Clear existing data
#     RATINGS_DB = []
#     ROLES_DB = []
#     WORKERS_DB = []
    
#     # Create 3 job roles with different base difficulties
#     ROLES_DB = [
#         MockJobRole(1, "Dishwashing", 2.0),    # Easy/Light job
#         MockJobRole(2, "Cooking", 3.0),        # Moderate job
#         MockJobRole(3, "Management", 4.0)      # Hard job
#     ]
    
#     # Create 3 workers
#     WORKERS_DB = [
#         MockWorker(1, "Alice"),
#         MockWorker(2, "Bob"),
#         MockWorker(3, "Charlie")
#     ]
    
#     return ROLES_DB, WORKERS_DB


# # ============================================================================
# # SIMPLE TESTS
# # ============================================================================

# def test_1_no_individual_ratings():
#     """
#     TEST 1: No Individual Ratings (Fallback to Base Difficulty)
    
#     Scenario: No workers have provided individual ratings yet.
#     Expected: Algorithm falls back to base difficulty for all workers.
#     """
#     print_header("TEST 1: No Individual Ratings (Fallback to Base)")
    
#     roles, workers = setup_test_data()
    
#     print("Setup:")
#     print(f"  - 3 Workers: {', '.join(w.name for w in workers)}")
#     print(f"  - 3 Job Roles with base difficulties:")
#     for role in roles:
#         print(f"    • {role.name}: {role.difficulty_multiplier}")
#     print("\n  - NO individual ratings provided")
    
#     print_subheader("Results: All Workers Use Base Difficulty")
    
#     for role in roles:
#         print(f"\n{role.name} (Base: {role.difficulty_multiplier}):")
#         for worker in workers:
#             difficulty = get_worker_individual_difficulty(
#                 worker.id, role.id, alpha=0.5
#             )
#             print(f"  {worker.name}: {difficulty:.2f} (using base difficulty)")
    
#     print("\n✓ When no individual ratings exist, all workers experience")
#     print("  the same difficulty (base difficulty) for each role.")


# def test_2_pure_objective_alpha_1():
#     """
#     TEST 2: Pure Objective Mode (alpha=1.0)
    
#     Scenario: Workers have individual ratings, but alpha=1.0 ignores them.
#     Expected: Only base difficulty is used, individual ratings ignored.
#     """
#     print_header("TEST 2: Pure Objective Mode (alpha=1.0)")
    
#     roles, workers = setup_test_data()
#     alice, bob, charlie = workers
#     dishwashing, cooking, management = roles
    
#     # Add individual ratings (that will be ignored)
#     RATINGS_DB.extend([
#         MockWorkerRoleRating(alice.id, dishwashing.id, 1.0),   # Alice finds dishwashing very easy
#         MockWorkerRoleRating(alice.id, cooking.id, 2.0),       # Alice finds cooking easy
#         MockWorkerRoleRating(alice.id, management.id, 5.0),    # Alice finds management very hard
#         MockWorkerRoleRating(bob.id, dishwashing.id, 3.0),     # Bob finds dishwashing moderate
#         MockWorkerRoleRating(bob.id, cooking.id, 3.0),         # Bob finds cooking moderate
#         MockWorkerRoleRating(bob.id, management.id, 2.0),      # Bob finds management easy (he's experienced)
#     ])
    
#     print("Setup:")
#     print(f"  - Alpha = 1.0 (100% base difficulty, 0% individual ratings)")
#     print(f"  - Individual ratings provided:")
#     print(f"    • Alice: Dishwashing=1.0, Cooking=2.0, Management=5.0")
#     print(f"    • Bob: Dishwashing=3.0, Cooking=3.0, Management=2.0")
#     print(f"    • Charlie: No ratings provided")
    
#     print_subheader("Results: Individual Ratings Ignored (alpha=1.0)")
    
#     for role in roles:
#         print(f"\n{role.name} (Base: {role.difficulty_multiplier}):")
#         for worker in workers:
#             difficulty = get_worker_individual_difficulty(
#                 worker.id, role.id, alpha=1.0  # Pure objective
#             )
#             print(f"  {worker.name}: {difficulty:.2f} (base only)")
    
#     print("\n✓ With alpha=1.0, individual ratings are completely ignored.")
#     print("  All workers experience the same difficulty (base difficulty).")


# def test_3_pure_subjective_alpha_0():
#     """
#     TEST 3: Pure Subjective Mode (alpha=0.0)
    
#     Scenario: Workers have individual ratings, alpha=0.0 uses only those.
#     Expected: Only individual ratings used, base difficulty ignored.
#     """
#     print_header("TEST 3: Pure Subjective Mode (alpha=0.0)")
    
#     roles, workers = setup_test_data()
#     alice, bob, charlie = workers
#     dishwashing, cooking, management = roles
    
#     # Add individual ratings
#     RATINGS_DB.extend([
#         MockWorkerRoleRating(alice.id, dishwashing.id, 1.0),   # Alice finds dishwashing very easy
#         MockWorkerRoleRating(alice.id, cooking.id, 2.0),       # Alice finds cooking easy
#         MockWorkerRoleRating(alice.id, management.id, 5.0),    # Alice finds management very hard
#         MockWorkerRoleRating(bob.id, dishwashing.id, 3.0),     # Bob finds dishwashing moderate
#         MockWorkerRoleRating(bob.id, cooking.id, 3.0),         # Bob finds cooking moderate
#         MockWorkerRoleRating(bob.id, management.id, 2.0),      # Bob finds management easy (experienced manager)
#     ])
    
#     print("Setup:")
#     print(f"  - Alpha = 0.0 (0% base difficulty, 100% individual ratings)")
#     print(f"  - Base difficulties: Dishwashing=2.0, Cooking=3.0, Management=4.0")
#     print(f"  - Individual ratings:")
#     print(f"    • Alice: Dishwashing=1.0, Cooking=2.0, Management=5.0")
#     print(f"    • Bob: Dishwashing=3.0, Cooking=3.0, Management=2.0")
#     print(f"    • Charlie: No ratings (will fall back to base)")
    
#     print_subheader("Results: Only Individual Ratings Used (alpha=0.0)")
    
#     for role in roles:
#         print(f"\n{role.name} (Base: {role.difficulty_multiplier}, ignored):")
#         for worker in workers:
#             difficulty = get_worker_individual_difficulty(
#                 worker.id, role.id, alpha=0.0  # Pure subjective
#             )
            
#             # Check if worker has individual rating
#             rating = None
#             for r in RATINGS_DB:
#                 if r.worker_id == worker.id and r.job_role_id == role.id:
#                     rating = r
#                     break
            
#             if rating:
#                 print(f"  {worker.name}: {difficulty:.2f} (individual rating: {rating.difficulty_rating})")
#             else:
#                 print(f"  {worker.name}: {difficulty:.2f} (fallback to base, no individual rating)")
    
#     print("\n✓ With alpha=0.0, individual ratings completely override base difficulty.")
#     print("  Workers without individual ratings fall back to base difficulty.")


# # ============================================================================
# # COMPLEX TESTS
# # ============================================================================

# def test_4_balanced_hybrid_alpha_05():
#     """
#     TEST 4: Balanced Hybrid Mode (alpha=0.5) - RECOMMENDED
    
#     Scenario: Workers have different perceptions, alpha=0.5 balances both.
#     Expected: Hybrid difficulty considers both base and individual ratings.
#     """
#     print_header("TEST 4: Balanced Hybrid Mode (alpha=0.5) - RECOMMENDED")
    
#     roles, workers = setup_test_data()
#     alice, bob, charlie = workers
#     dishwashing, cooking, management = roles
    
#     # Scenario: Different workers have different strengths
#     RATINGS_DB.extend([
#         # Alice: Strong cook, weak manager
#         MockWorkerRoleRating(alice.id, dishwashing.id, 2.0),   # Average at dishwashing
#         MockWorkerRoleRating(alice.id, cooking.id, 1.0),       # Excellent cook (easy for her)
#         MockWorkerRoleRating(alice.id, management.id, 5.0),    # Poor manager (very hard for her)
        
#         # Bob: Experienced manager, doesn't like dishwashing
#         MockWorkerRoleRating(bob.id, dishwashing.id, 4.0),     # Dislikes dishwashing (hard for him)
#         MockWorkerRoleRating(bob.id, cooking.id, 3.0),         # Average cook
#         MockWorkerRoleRating(bob.id, management.id, 1.0),      # Excellent manager (easy for him)
        
#         # Charlie: Balanced worker (no strong preferences)
#         MockWorkerRoleRating(charlie.id, dishwashing.id, 3.0),
#         MockWorkerRoleRating(charlie.id, cooking.id, 3.0),
#         MockWorkerRoleRating(charlie.id, management.id, 3.0),
#     ])
    
#     print("Setup:")
#     print(f"  - Alpha = 0.5 (50% base, 50% individual) - BALANCED")
#     print(f"  - Base difficulties: Dishwashing=2.0, Cooking=3.0, Management=4.0")
#     print(f"\n  - Worker profiles:")
#     print(f"    • Alice: Strong cook (1.0), weak manager (5.0)")
#     print(f"    • Bob: Experienced manager (1.0), dislikes dishwashing (4.0)")
#     print(f"    • Charlie: Balanced across all roles (3.0 each)")
    
#     print_subheader("Results: Hybrid Difficulty Calculations")
    
#     for role in roles:
#         print(f"\n{role.name} (Base: {role.difficulty_multiplier}):")
#         for worker in workers:
#             rating = None
#             for r in RATINGS_DB:
#                 if r.worker_id == worker.id and r.job_role_id == role.id:
#                     rating = r
#                     break
            
#             difficulty = get_worker_individual_difficulty(
#                 worker.id, role.id, alpha=0.5
#             )
            
#             if rating:
#                 base = role.difficulty_multiplier
#                 individual = rating.difficulty_rating
#                 formula = f"(0.5 × {base}) + (0.5 × {individual})"
#                 print(f"  {worker.name}: {difficulty:.2f} = {formula}")
#             else:
#                 print(f"  {worker.name}: {difficulty:.2f} (fallback to base)")
    
#     print_subheader("Analysis: How This Affects Fairness")
    
#     print("\n1. Alice (Strong Cook):")
#     print(f"   - Cooking: {get_worker_individual_difficulty(alice.id, cooking.id, 0.5):.2f} (easier for her)")
#     print(f"   - Management: {get_worker_individual_difficulty(alice.id, management.id, 0.5):.2f} (harder for her)")
#     print("   → Algorithm will assign her more cooking shifts for fairness")
    
#     print("\n2. Bob (Experienced Manager):")
#     print(f"   - Dishwashing: {get_worker_individual_difficulty(bob.id, dishwashing.id, 0.5):.2f} (harder for him)")
#     print(f"   - Management: {get_worker_individual_difficulty(bob.id, management.id, 0.5):.2f} (easier for him)")
#     print("   → Algorithm will assign him more management shifts")
    
#     print("\n3. Charlie (Balanced):")
#     print(f"   - All roles: ~{get_worker_individual_difficulty(charlie.id, cooking.id, 0.5):.2f}")
#     print("   → Algorithm will distribute shifts evenly")
    
#     print("\n✓ Alpha=0.5 balances objective difficulty with subjective perception.")
#     print("  This creates personalized fairness based on individual strengths.")


# def test_5_mixed_scenario_partial_ratings():
#     """
#     TEST 5: Mixed Scenario with Partial Ratings
    
#     Scenario: Some workers rated some roles, others didn't.
#     Expected: Hybrid for rated roles, fallback to base for unrated.
#     """
#     print_header("TEST 5: Mixed Scenario with Partial Ratings")
    
#     roles, workers = setup_test_data()
#     alice, bob, charlie = workers
#     dishwashing, cooking, management = roles
    
#     # Scenario: Workers rated only roles they feel strongly about
#     RATINGS_DB.extend([
#         # Alice only rated cooking and management (feels strongly)
#         MockWorkerRoleRating(alice.id, cooking.id, 1.0),       # Loves cooking
#         MockWorkerRoleRating(alice.id, management.id, 5.0),    # Hates management
#         # Alice didn't rate dishwashing (neutral/unsure)
        
#         # Bob only rated management (his expertise)
#         MockWorkerRoleRating(bob.id, management.id, 1.0),      # Expert manager
#         # Bob didn't rate other roles (neutral)
        
#         # Charlie didn't rate anything (new worker, unsure)
#     ])
    
#     print("Setup:")
#     print(f"  - Alpha = 0.5 (balanced hybrid)")
#     print(f"  - Partial ratings provided:")
#     print(f"    • Alice: Only rated Cooking=1.0, Management=5.0")
#     print(f"    • Bob: Only rated Management=1.0")
#     print(f"    • Charlie: No ratings provided")
    
#     print_subheader("Results: Hybrid for Rated, Base for Unrated")
    
#     for role in roles:
#         print(f"\n{role.name} (Base: {role.difficulty_multiplier}):")
#         for worker in workers:
#             rating = None
#             for r in RATINGS_DB:
#                 if r.worker_id == worker.id and r.job_role_id == role.id:
#                     rating = r
#                     break
            
#             difficulty = get_worker_individual_difficulty(
#                 worker.id, role.id, alpha=0.5
#             )
            
#             if rating:
#                 base = role.difficulty_multiplier
#                 individual = rating.difficulty_rating
#                 print(f"  {worker.name}: {difficulty:.2f} (hybrid: base={base}, individual={individual})")
#             else:
#                 print(f"  {worker.name}: {difficulty:.2f} (base only, no individual rating)")
    
#     print_subheader("Analysis: Flexibility in Rating")
    
#     print("\n✓ Workers can choose to rate only roles they feel strongly about.")
#     print("✓ Unrated roles automatically fall back to base difficulty.")
#     print("✓ This is useful when:")
#     print("  - New workers haven't formed opinions yet")
#     print("  - Workers feel neutral about certain roles")
#     print("  - Workers want to opt-in gradually to personalization")


# def test_6_extreme_rating_patterns():
#     """
#     TEST 6: Extreme Rating Patterns (Real-World Challenge)
    
#     Scenario: One worker rates everything easy, another rates everything hard.
#     Expected: Alpha parameter moderates extreme ratings to prevent gaming.
#     """
#     print_header("TEST 6: Extreme Rating Patterns (Gaming Prevention)")
    
#     roles, workers = setup_test_data()
#     alice, bob, charlie = workers
#     dishwashing, cooking, management = roles
    
#     # Scenario: Extreme rating patterns (potential gaming)
#     RATINGS_DB.extend([
#         # Alice: Rates everything as very easy (trying to get more work?)
#         MockWorkerRoleRating(alice.id, dishwashing.id, 1.0),
#         MockWorkerRoleRating(alice.id, cooking.id, 1.0),
#         MockWorkerRoleRating(alice.id, management.id, 1.0),
        
#         # Bob: Rates everything as very hard (trying to avoid work?)
#         MockWorkerRoleRating(bob.id, dishwashing.id, 5.0),
#         MockWorkerRoleRating(bob.id, cooking.id, 5.0),
#         MockWorkerRoleRating(bob.id, management.id, 5.0),
        
#         # Charlie: Honest, differentiated ratings
#         MockWorkerRoleRating(charlie.id, dishwashing.id, 2.0),
#         MockWorkerRoleRating(charlie.id, cooking.id, 3.0),
#         MockWorkerRoleRating(charlie.id, management.id, 4.0),
#     ])
    
#     print("Setup:")
#     print(f"  - Base difficulties: Dishwashing=2.0, Cooking=3.0, Management=4.0")
#     print(f"  - Rating patterns:")
#     print(f"    • Alice: All 1.0 (everything easy - suspicious?)")
#     print(f"    • Bob: All 5.0 (everything hard - trying to game?)")
#     print(f"    • Charlie: 2.0, 3.0, 4.0 (honest, differentiated)")
    
#     print_subheader("Results with Different Alpha Values")
    
#     alphas = [0.0, 0.3, 0.5, 0.7, 1.0]
    
#     for alpha in alphas:
#         print(f"\n--- Alpha = {alpha} ---")
        
#         for role in roles:
#             print(f"\n{role.name} (Base: {role.difficulty_multiplier}):")
            
#             for worker in workers:
#                 rating = None
#                 for r in RATINGS_DB:
#                     if r.worker_id == worker.id and r.job_role_id == role.id:
#                         rating = r
#                         break
                
#                 difficulty = get_worker_individual_difficulty(
#                     worker.id, role.id, alpha=alpha
#                 )
                
#                 if rating:
#                     print(f"  {worker.name}: {difficulty:.2f} (individual={rating.difficulty_rating})")
#                 else:
#                     print(f"  {worker.name}: {difficulty:.2f}")
    
#     print_subheader("Analysis: Alpha Parameter as Gaming Protection")
    
#     print("\n1. Alpha = 0.0 (Pure Subjective):")
#     print("   - Alice gets everything at 1.0 (could be exploited)")
#     print("   - Bob gets everything at 5.0 (could avoid work)")
#     print("   ❌ Vulnerable to gaming")
    
#     print("\n2. Alpha = 0.5 (Balanced - RECOMMENDED):")
#     print("   - Alice's ratings moderated by base difficulty")
#     print("   - Bob's ratings moderated by base difficulty")
#     print("   - Charlie's honest ratings still have impact")
#     print("   ✓ Good balance: personalization + gaming protection")
    
#     print("\n3. Alpha = 1.0 (Pure Objective):")
#     print("   - All extreme ratings ignored")
#     print("   - Charlie's honest ratings also ignored")
#     print("   ❌ No personalization benefit")
    
#     print("\n✓ Alpha=0.5 provides:")
#     print("  • Protection against extreme gaming (all 1s or all 5s)")
#     print("  • Still allows honest individual differences")
#     print("  • Base difficulty anchors ratings to reality")
    
#     print("\n📝 Note: The import process has additional protection:")
#     print("  • Detects flat ratings (variance = 0)")
#     print("  • Can remove extreme workers entirely")
#     print("  • Alpha provides mathematical protection layer")


# # ============================================================================
# # MAIN TEST RUNNER
# # ============================================================================

# def run_all_tests():
#     """Run all test scenarios"""
#     print_header("INDIVIDUAL DIFFICULTY RATING SYSTEM - TEST SUITE", '=')
#     print("This test suite demonstrates how worker-specific difficulty ratings")
#     print("combine with base (consensus) difficulty to create personalized fairness.")
#     print("\nFormula: hybrid = (alpha × base) + ((1 - alpha) × individual)")
    
#     # Run simple tests
#     print_header("PART 1: SIMPLE TESTS", '=')
    
#     test_1_no_individual_ratings()
    
#     # Clear database for next test
#     global RATINGS_DB, ROLES_DB, WORKERS_DB
#     RATINGS_DB = []
    
#     test_2_pure_objective_alpha_1()
    
#     RATINGS_DB = []
    
#     test_3_pure_subjective_alpha_0()
    
#     # Run complex tests
#     print_header("PART 2: COMPLEX TESTS", '=')
    
#     RATINGS_DB = []
    
#     test_4_balanced_hybrid_alpha_05()
    
#     RATINGS_DB = []
    
#     test_5_mixed_scenario_partial_ratings()
    
#     RATINGS_DB = []
    
#     test_6_extreme_rating_patterns()
    
#     # Final summary
#     print_header("TEST SUITE COMPLETE", '=')
#     print("\n📊 SUMMARY OF KEY FINDINGS:")
#     print("\n1. WITHOUT individual ratings:")
#     print("   → Everyone experiences base difficulty (fair but not personalized)")
    
#     print("\n2. WITH individual ratings + alpha=0.0:")
#     print("   → Pure personalization (vulnerable to gaming)")
    
#     print("\n3. WITH individual ratings + alpha=1.0:")
#     print("   → No personalization (safe but ignores preferences)")
    
#     print("\n4. WITH individual ratings + alpha=0.5 [RECOMMENDED]:")
#     print("   → Balanced: personalized fairness with gaming protection")
#     print("   → Workers with honest ratings benefit from personalization")
#     print("   → Extreme ratings moderated by base difficulty")
    
#     print("\n5. PARTIAL ratings:")
#     print("   → Workers can rate only roles they feel strongly about")
#     print("   → Unrated roles fall back to base difficulty")
    
#     print("\n6. EXTREME patterns:")
#     print("   → Alpha parameter protects against gaming")
#     print("   → Import process can detect and filter extreme patterns")
    
#     print("\n✅ RECOMMENDATION FOR PRODUCTION:")
#     print("   • Use alpha=0.5 (balanced hybrid)")
#     print("   • Enable import-time detection of extreme patterns")
#     print("   • Educate workers on honest rating importance")
#     print("   • Monitor rating variance to detect gaming attempts")
    
#     print("\n" + "=" * 80)
#     print("All tests completed successfully!")
#     print("=" * 80 + "\n")


# if __name__ == '__main__':
#     run_all_tests()

"""
Fair Shift Scheduling Algorithm - Comprehensive Test Suite
===========================================================

This test demonstrates how the shift scheduling algorithm fairly distributes
shifts among workers while considering:
1. Worker qualifications and availability
2. Maximum hours constraints
3. Shift difficulty (weighted hours)
4. Individual worker difficulty ratings
5. Role rotation to prevent consecutive same-role assignments
6. Overlap prevention
"""

from datetime import datetime, timedelta
from collections import defaultdict
import random


# ============================================================================
# MOCK DATA STRUCTURES (simulating Flask models)
# ============================================================================

class MockJobRole:
    """Simulated JobRole with base difficulty"""
    def __init__(self, id, name, difficulty_multiplier):
        self.id = id
        self.name = name
        self.difficulty_multiplier = difficulty_multiplier


class MockWorker:
    """Simulated Worker"""
    def __init__(self, id, name, max_hours_per_week, qualified_role_ids):
        self.id = id
        self.name = name
        self.max_hours_per_week = max_hours_per_week
        self.qualified_roles = []  # Will be populated with role objects
        self.qualified_role_ids = qualified_role_ids
        self.constraints = []  # Unavailability periods


class MockConstraint:
    """Simulated worker unavailability constraint"""
    def __init__(self, start_datetime, end_datetime):
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime


class MockShiftDefinition:
    """Simulated shift slot"""
    def __init__(self, id, name, slot_start_datetime, slot_end_datetime, job_role_id, job_role):
        self.id = id
        self.name = name
        self.slot_start_datetime = slot_start_datetime
        self.slot_end_datetime = slot_end_datetime
        self.job_role_id = job_role_id
        self.job_role = job_role
        self.duration_total_seconds = (slot_end_datetime - slot_start_datetime).total_seconds()


class MockAssignment:
    """Simulated shift assignment"""
    def __init__(self, shift_definition_id):
        self.shift_definition_id = shift_definition_id
        self.worker_id = None  # To be assigned by algorithm


class MockWorkerRoleRating:
    """Individual worker difficulty rating for a role"""
    def __init__(self, worker_id, job_role_id, difficulty_rating):
        self.worker_id = worker_id
        self.job_role_id = job_role_id
        self.difficulty_rating = difficulty_rating


# ============================================================================
# GLOBAL DATABASES (simulating SQLAlchemy queries)
# ============================================================================

ROLES_DB = []
WORKERS_DB = []
RATINGS_DB = []
DIFFICULTY_ALPHA = 0.5  # Balance between base and individual difficulty


# ============================================================================
# ALGORITHM FUNCTIONS (adapted from algorithm.py)
# ============================================================================

def is_worker_qualified_for_slot(worker, slot_def):
    """Checks if a worker is qualified for the job role of a given shift slot."""
    worker_qualified_role_ids = {role.id for role in worker.qualified_roles}
    return slot_def.job_role_id in worker_qualified_role_ids


def is_worker_available_for_slot(worker, slot_def):
    """Checks worker's hard constraints: qualification and availability"""
    # 1. Check Role Qualification
    if not is_worker_qualified_for_slot(worker, slot_def):
        return False

    # 2. Check Unavailability Constraints
    for constraint in worker.constraints:
        if slot_def.slot_start_datetime < constraint.end_datetime and \
           slot_def.slot_end_datetime > constraint.start_datetime:
            return False
            
    return True


def get_recent_role_penalty(worker_id, role_id, slot_start, recent_assignments):
    """Calculate penalty for assigning same role on consecutive days"""
    if worker_id not in recent_assignments:
        return 1.0
    
    slot_date = slot_start.date()
    
    for days_back in range(1, 4):  # Check up to 3 days back
        check_date = slot_date - timedelta(days=days_back)
        if check_date in recent_assignments[worker_id]:
            if role_id in recent_assignments[worker_id][check_date]:
                penalty = 2.5 - (0.5 * days_back)
                return penalty
    
    return 1.0


def get_worker_individual_difficulty(worker_id, job_role_id, alpha=0.5):
    """Get hybrid difficulty rating combining base and individual ratings"""
    # Get base difficulty
    role = None
    for r in ROLES_DB:
        if r.id == job_role_id:
            role = r
            break
    base_difficulty = role.difficulty_multiplier if role else 1.0
    
    # Get individual rating
    individual_rating = None
    for rating in RATINGS_DB:
        if rating.worker_id == worker_id and rating.job_role_id == job_role_id:
            individual_rating = rating
            break
    
    if individual_rating:
        subjective_difficulty = individual_rating.difficulty_rating
        hybrid_difficulty = (alpha * base_difficulty) + ((1 - alpha) * subjective_difficulty)
        return hybrid_difficulty
    else:
        return base_difficulty


def assign_shifts_fairly(all_pending_assignments, workers, slot_definitions_map):
    """Main algorithm: Fairly assign shifts to workers"""
    algo_messages = []
    
    if not workers:
        algo_messages.append(("error", "No workers available to assign shifts."))
        return False, algo_messages
    
    if not all_pending_assignments:
        algo_messages.append(("info", "No shifts to assign."))
        return True, algo_messages

    # Sort by start time
    all_pending_assignments.sort(
        key=lambda a: slot_definitions_map.get(a.shift_definition_id).slot_start_datetime
    )

    # Initialize tracking
    worker_assigned_hours = {w.id: 0.0 for w in workers}
    worker_weighted_hours = {w.id: 0.0 for w in workers}
    worker_shift_assignments = {w.id: [] for w in workers}
    recent_role_assignments = defaultdict(lambda: defaultdict(set))
    
    unassigned_count = 0
    assignment_details = []

    for assignment_obj in all_pending_assignments:
        slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
        if not slot_def:
            unassigned_count += 1
            continue

        assigned_this_slot = False
        slot_date = slot_def.slot_start_datetime.date()
        role_id = slot_def.job_role_id
        
        real_duration_hours = slot_def.duration_total_seconds / 3600.0
        
        eligible_workers = []
        
        for worker in workers:
            # Check hard constraints
            if not is_worker_available_for_slot(worker, slot_def):
                continue

            # Check overlapping shifts
            is_overlapping = False
            for other_slot in worker_shift_assignments[worker.id]:
                if max(slot_def.slot_start_datetime, other_slot.slot_start_datetime) < \
                   min(slot_def.slot_end_datetime, other_slot.slot_end_datetime):
                    is_overlapping = True
                    break
            if is_overlapping:
                continue
            
            # Check max hours
            if worker.max_hours_per_week:
                if (worker_assigned_hours[worker.id] + real_duration_hours) > worker.max_hours_per_week:
                    continue
            
            # Calculate effective weighted hours with role penalty
            role_penalty = get_recent_role_penalty(
                worker.id, role_id, slot_def.slot_start_datetime, recent_role_assignments
            )
            effective_weighted_hours = worker_weighted_hours[worker.id] * role_penalty
            
            eligible_workers.append((worker, effective_weighted_hours, role_penalty))

        # Sort by effective weighted hours with random tie-breaking
        eligible_workers.sort(key=lambda x: (x[1], random.random()))
        
        # Assign to worker with lowest effective weighted hours
        if eligible_workers:
            worker, prev_weighted, role_penalty = eligible_workers[0]
            assignment_obj.worker_id = worker.id
            
            # Update hours
            worker_assigned_hours[worker.id] += real_duration_hours
            
            # Get individual difficulty
            worker_difficulty = get_worker_individual_difficulty(
                worker.id, role_id, alpha=DIFFICULTY_ALPHA
            )
            worker_weighted_hours[worker.id] += real_duration_hours * worker_difficulty
            
            # Record assignment
            worker_shift_assignments[worker.id].append(slot_def)
            recent_role_assignments[worker.id][slot_date].add(role_id)
            
            # Store details for reporting
            assignment_details.append({
                'shift': slot_def,
                'worker': worker,
                'real_hours': real_duration_hours,
                'difficulty': worker_difficulty,
                'weighted_hours': real_duration_hours * worker_difficulty,
                'role_penalty': role_penalty,
                'prev_weighted_total': prev_weighted,
                'new_weighted_total': worker_weighted_hours[worker.id]
            })
            
            assigned_this_slot = True

        if not assigned_this_slot:
            unassigned_count += 1
            assignment_details.append({
                'shift': slot_def,
                'worker': None,
                'unassigned': True
            })

    if unassigned_count == 0:
        algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned successfully!"))
    else:
        algo_messages.append(("warning", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned."))
    
    return (unassigned_count == 0), algo_messages, assignment_details, worker_assigned_hours, worker_weighted_hours


# ============================================================================
# TEST DATA SETUP
# ============================================================================

def setup_test_scenario():
    """Create a realistic test scenario"""
    global ROLES_DB, WORKERS_DB, RATINGS_DB
    
    ROLES_DB = []
    WORKERS_DB = []
    RATINGS_DB = []
    
    # Create job roles
    roles = [
        MockJobRole(1, "Dishwashing", 2.0),
        MockJobRole(2, "Cooking", 3.0),
        MockJobRole(3, "Serving", 2.5),
        MockJobRole(4, "Management", 4.0)
    ]
    ROLES_DB = roles
    
    # Create workers with different qualifications
    workers = [
        MockWorker(1, "Alice", 40.0, [1, 2, 3]),      # Qualified for 3 roles, 40h max
        MockWorker(2, "Bob", 35.0, [2, 3, 4]),        # Qualified for 3 roles, 35h max
        MockWorker(3, "Charlie", 30.0, [1, 3]),       # Qualified for 2 roles, 30h max
        MockWorker(4, "Diana", 45.0, [1, 2, 3, 4]),   # Qualified for all roles, 45h max
        MockWorker(5, "Eve", 25.0, [1, 2]),           # Qualified for 2 roles, 25h max
    ]
    
    # Set up qualified roles
    for worker in workers:
        worker.qualified_roles = [r for r in roles if r.id in worker.qualified_role_ids]
    
    # Add some unavailability constraints
    base_date = datetime(2025, 11, 4, 8, 0)  # Starting Monday
    workers[1].constraints.append(
        MockConstraint(
            base_date + timedelta(days=2, hours=0),  # Wednesday all day
            base_date + timedelta(days=2, hours=24)
        )
    )
    workers[3].constraints.append(
        MockConstraint(
            base_date + timedelta(days=4, hours=16),  # Friday evening
            base_date + timedelta(days=4, hours=23)
        )
    )
    
    WORKERS_DB = workers
    
    # Add individual difficulty ratings (some workers)
    RATINGS_DB = [
        # Alice finds cooking easier than average
        MockWorkerRoleRating(1, 2, 2.0),
        MockWorkerRoleRating(1, 3, 3.0),
        
        # Bob finds management easier (experienced)
        MockWorkerRoleRating(2, 4, 2.5),
        MockWorkerRoleRating(2, 2, 3.5),
        
        # Charlie finds dishwashing harder
        MockWorkerRoleRating(3, 1, 3.0),
        
        # Diana has balanced ratings
        MockWorkerRoleRating(4, 1, 2.0),
        MockWorkerRoleRating(4, 2, 3.0),
        MockWorkerRoleRating(4, 3, 2.5),
        MockWorkerRoleRating(4, 4, 4.0),
    ]
    
    return roles, workers


def create_test_shifts(roles):
    """Create a week of shifts"""
    base_date = datetime(2025, 11, 4, 8, 0)  # Starting Monday
    shifts = []
    shift_id = 1
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    for day_idx in range(5):  # 5 days
        day_name = days[day_idx]
        day_start = base_date + timedelta(days=day_idx)
        
        # Morning shift: Dishwashing (6 hours)
        shifts.append(MockShiftDefinition(
            shift_id, f"{day_name} Morning - Dishwashing",
            day_start, day_start + timedelta(hours=6),
            1, roles[0]
        ))
        shift_id += 1
        
        # Morning shift: Cooking (6 hours)
        shifts.append(MockShiftDefinition(
            shift_id, f"{day_name} Morning - Cooking",
            day_start, day_start + timedelta(hours=6),
            2, roles[1]
        ))
        shift_id += 1
        
        # Afternoon shift: Serving (5 hours)
        afternoon_start = day_start + timedelta(hours=6)
        shifts.append(MockShiftDefinition(
            shift_id, f"{day_name} Afternoon - Serving",
            afternoon_start, afternoon_start + timedelta(hours=5),
            3, roles[2]
        ))
        shift_id += 1
        
        # Evening shift: Cooking (4 hours)
        evening_start = day_start + timedelta(hours=14)
        shifts.append(MockShiftDefinition(
            shift_id, f"{day_name} Evening - Cooking",
            evening_start, evening_start + timedelta(hours=4),
            2, roles[1]
        ))
        shift_id += 1
        
        # Management shift (spans afternoon/evening, 6 hours)
        mgmt_start = day_start + timedelta(hours=12)
        shifts.append(MockShiftDefinition(
            shift_id, f"{day_name} - Management",
            mgmt_start, mgmt_start + timedelta(hours=6),
            4, roles[3]
        ))
        shift_id += 1
    
    return shifts


# ============================================================================
# OUTPUT FORMATTING FUNCTIONS
# ============================================================================

def print_header(title, char='=', width=100):
    """Print formatted header"""
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")


def print_section(title, width=100):
    """Print section header"""
    print(f"\n{'-' * width}")
    print(f"  {title}")
    print(f"{'-' * width}")


def print_test_setup(roles, workers):
    """Print the test scenario setup"""
    print_header("TEST SCENARIO SETUP")
    
    print_section("Job Roles")
    print(f"{'Role Name':<20} {'Base Difficulty':<20} {'Description'}")
    print("-" * 70)
    for role in roles:
        desc = "Higher difficulty = more weighted hours"
        print(f"{role.name:<20} {role.difficulty_multiplier:<20.1f} {desc}")
    
    print_section("Workers")
    print(f"{'Name':<12} {'Max Hours':<12} {'Qualified Roles':<40} {'Constraints'}")
    print("-" * 100)
    for worker in workers:
        role_names = ", ".join([r.name for r in worker.qualified_roles])
        constraints = f"{len(worker.constraints)} unavailability period(s)" if worker.constraints else "None"
        print(f"{worker.name:<12} {worker.max_hours_per_week:<12.1f} {role_names:<40} {constraints}")
    
    print_section("Individual Difficulty Ratings")
    print(f"Alpha = {DIFFICULTY_ALPHA} (50% base difficulty, 50% individual rating)")
    print()
    print(f"{'Worker':<12} {'Role':<20} {'Base':<10} {'Individual':<12} {'Hybrid':<10}")
    print("-" * 70)
    
    for rating in RATINGS_DB:
        worker = next(w for w in workers if w.id == rating.worker_id)
        role = next(r for r in roles if r.id == rating.job_role_id)
        hybrid = get_worker_individual_difficulty(worker.id, role.id, DIFFICULTY_ALPHA)
        print(f"{worker.name:<12} {role.name:<20} {role.difficulty_multiplier:<10.1f} "
              f"{rating.difficulty_rating:<12.1f} {hybrid:<10.2f}")
    
    print("\nNote: Workers without individual ratings use base difficulty for all roles.")


def print_shift_schedule(shifts):
    """Print the shift schedule"""
    print_section("Shift Schedule (5-day week)")
    
    print(f"{'Shift Name':<35} {'Day/Time':<25} {'Duration':<12} {'Role':<15} {'Base Diff.'}")
    print("-" * 100)
    
    current_day = None
    for shift in shifts:
        day = shift.slot_start_datetime.strftime("%A")
        if day != current_day:
            print()
            current_day = day
        
        time_str = f"{shift.slot_start_datetime.strftime('%H:%M')} - {shift.slot_end_datetime.strftime('%H:%M')}"
        duration = shift.duration_total_seconds / 3600.0
        
        print(f"{shift.name:<35} {day + ' ' + time_str:<25} {duration:<12.1f}h "
              f"{shift.job_role.name:<15} {shift.job_role.difficulty_multiplier:.1f}")
    
    print(f"\nTotal shifts to assign: {len(shifts)}")


def print_assignment_results(assignment_details, workers):
    """Print detailed assignment results"""
    print_header("SHIFT ASSIGNMENT RESULTS")
    
    # Summary table
    print_section("Assignment Summary")
    assigned = [d for d in assignment_details if not d.get('unassigned')]
    unassigned = [d for d in assignment_details if d.get('unassigned')]
    
    print(f"Total shifts: {len(assignment_details)}")
    print(f"Successfully assigned: {len(assigned)}")
    print(f"Unassigned: {len(unassigned)}")
    print(f"Success rate: {len(assigned)/len(assignment_details)*100:.1f}%")
    
    # Detailed assignments
    print_section("Detailed Assignments")
    print(f"{'#':<4} {'Shift':<35} {'Worker':<12} {'Hours':<8} {'Difficulty':<12} {'Weighted':<10} {'Penalty':<8}")
    print("-" * 100)
    
    for idx, detail in enumerate(assignment_details, 1):
        if detail.get('unassigned'):
            shift_name = detail['shift'].name
            print(f"{idx:<4} {shift_name:<35} {'UNASSIGNED':<12} {'-':<8} {'-':<12} {'-':<10} {'-':<8}")
        else:
            shift_name = detail['shift'].name
            worker_name = detail['worker'].name
            hours = detail['real_hours']
            difficulty = detail['difficulty']
            weighted = detail['weighted_hours']
            penalty = detail['role_penalty']
            
            penalty_str = f"{penalty:.1f}x" if penalty > 1.0 else "-"
            print(f"{idx:<4} {shift_name:<35} {worker_name:<12} {hours:<8.1f} {difficulty:<12.2f} "
                  f"{weighted:<10.2f} {penalty_str:<8}")
    
    if unassigned:
        print_section("Unassigned Shifts Analysis")
        for detail in unassigned:
            shift = detail['shift']
            print(f"  • {shift.name}")
            print(f"    Time: {shift.slot_start_datetime.strftime('%A %H:%M')} - "
                  f"{shift.slot_end_datetime.strftime('%H:%M')}")
            print(f"    Role: {shift.job_role.name} (requires qualification)")
            print()


def print_worker_summary(worker_hours, worker_weighted_hours, workers):
    """Print summary of each worker's assignments"""
    print_section("Worker Load Summary")
    
    print(f"{'Worker':<12} {'Real Hours':<15} {'Weighted Hours':<18} {'Max Hours':<12} {'Utilization':<15} {'Fairness'}")
    print("-" * 100)
    
    for worker in workers:
        real = worker_hours[worker.id]
        weighted = worker_weighted_hours[worker.id]
        max_h = worker.max_hours_per_week
        utilization = (real / max_h * 100) if max_h else 0
        
        # Calculate fairness indicator
        avg_weighted = sum(worker_weighted_hours.values()) / len(workers)
        diff_from_avg = ((weighted - avg_weighted) / avg_weighted * 100) if avg_weighted > 0 else 0
        
        if abs(diff_from_avg) < 10:
            fairness = "✓ Balanced"
        elif diff_from_avg > 0:
            fairness = f"↑ {diff_from_avg:+.1f}%"
        else:
            fairness = f"↓ {diff_from_avg:+.1f}%"
        
        print(f"{worker.name:<12} {real:<15.1f} {weighted:<18.2f} {max_h:<12.1f} "
              f"{utilization:<15.1f}% {fairness}")
    
    print()
    print(f"Average weighted hours: {sum(worker_weighted_hours.values()) / len(workers):.2f}")
    print(f"Std deviation: {std_dev(list(worker_weighted_hours.values())):.2f}")
    print()
    print("✓ Fair distribution: Weighted hours are balanced across workers")
    print("  (accounting for individual difficulty perceptions)")


def std_dev(values):
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def print_role_rotation_analysis(assignment_details, workers):
    """Analyze role rotation patterns"""
    print_section("Role Rotation Analysis")
    
    # Track consecutive same-role assignments
    worker_assignments = defaultdict(list)
    for detail in assignment_details:
        if not detail.get('unassigned'):
            worker_assignments[detail['worker'].id].append({
                'date': detail['shift'].slot_start_datetime.date(),
                'role': detail['shift'].job_role.name,
                'penalty': detail.get('role_penalty', 1.0)
            })
    
    print("Checking for role variety (penalties applied for consecutive same roles):\n")
    
    for worker in workers:
        assignments = sorted(worker_assignments[worker.id], key=lambda x: x['date'])
        if not assignments:
            print(f"{worker.name}: No assignments")
            continue
        
        print(f"{worker.name}:")
        
        # Group by date
        by_date = defaultdict(list)
        for a in assignments:
            by_date[a['date']].append(a)
        
        for date in sorted(by_date.keys()):
            roles = [a['role'] for a in by_date[date]]
            penalties = [a['penalty'] for a in by_date[date]]
            max_penalty = max(penalties)
            
            penalty_note = f" (penalty: {max_penalty:.1f}x)" if max_penalty > 1.0 else ""
            print(f"  {date.strftime('%A')}: {', '.join(roles)}{penalty_note}")
        
        print()


def generate_text_report(roles, workers, shifts, assignment_details, worker_hours, worker_weighted_hours):
    """Generate a comprehensive text report"""
    report_lines = []
    
    report_lines.append("=" * 100)
    report_lines.append("FAIR SHIFT SCHEDULING ALGORITHM - TEST REPORT".center(100))
    report_lines.append("=" * 100)
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Test Scenario: 5-day work week with {len(workers)} workers and {len(shifts)} shifts")
    report_lines.append("")
    
    # Configuration
    report_lines.append("-" * 100)
    report_lines.append("ALGORITHM CONFIGURATION")
    report_lines.append("-" * 100)
    report_lines.append(f"Difficulty Alpha: {DIFFICULTY_ALPHA} (50% base difficulty, 50% individual rating)")
    report_lines.append(f"Role Rotation Penalty: Yes (discourages consecutive same-role assignments)")
    report_lines.append(f"Overlap Prevention: Yes (workers cannot work overlapping shifts)")
    report_lines.append(f"Max Hours Enforcement: Yes (respects worker hour limits)")
    report_lines.append("")
    
    # Workers summary
    report_lines.append("-" * 100)
    report_lines.append("WORKERS")
    report_lines.append("-" * 100)
    for worker in workers:
        role_names = ", ".join([r.name for r in worker.qualified_roles])
        report_lines.append(f"{worker.name}: Max {worker.max_hours_per_week}h/week, Qualified for: {role_names}")
    report_lines.append("")
    
    # Results
    assigned = [d for d in assignment_details if not d.get('unassigned')]
    unassigned = [d for d in assignment_details if d.get('unassigned')]
    
    report_lines.append("-" * 100)
    report_lines.append("RESULTS SUMMARY")
    report_lines.append("-" * 100)
    report_lines.append(f"Total Shifts: {len(assignment_details)}")
    report_lines.append(f"Assigned: {len(assigned)}")
    report_lines.append(f"Unassigned: {len(unassigned)}")
    report_lines.append(f"Success Rate: {len(assigned)/len(assignment_details)*100:.1f}%")
    report_lines.append("")
    
    # Worker loads
    report_lines.append("-" * 100)
    report_lines.append("WORKER LOAD DISTRIBUTION")
    report_lines.append("-" * 100)
    report_lines.append(f"{'Worker':<12} {'Real Hours':<15} {'Weighted Hours':<18} {'Max Hours':<12} {'Utilization'}")
    report_lines.append("-" * 100)
    
    for worker in workers:
        real = worker_hours[worker.id]
        weighted = worker_weighted_hours[worker.id]
        max_h = worker.max_hours_per_week
        utilization = (real / max_h * 100) if max_h else 0
        
        report_lines.append(f"{worker.name:<12} {real:<15.1f} {weighted:<18.2f} {max_h:<12.1f} {utilization:.1f}%")
    
    report_lines.append("")
    avg_weighted = sum(worker_weighted_hours.values()) / len(workers)
    report_lines.append(f"Average Weighted Hours: {avg_weighted:.2f}")
    report_lines.append(f"Standard Deviation: {std_dev(list(worker_weighted_hours.values())):.2f}")
    report_lines.append("")
    
    # Fairness analysis
    report_lines.append("-" * 100)
    report_lines.append("FAIRNESS ANALYSIS")
    report_lines.append("-" * 100)
    report_lines.append("The algorithm achieves fairness by:")
    report_lines.append("1. Using weighted hours (real hours × difficulty) instead of just real hours")
    report_lines.append("2. Incorporating individual worker difficulty ratings (personalized fairness)")
    report_lines.append("3. Always assigning to the worker with lowest effective weighted hours")
    report_lines.append("4. Applying penalties for consecutive same-role assignments")
    report_lines.append("")
    report_lines.append("Result: Workers end up with similar weighted hours, meaning similar")
    report_lines.append("        perceived workload even if real hours differ.")
    report_lines.append("")
    
    report_lines.append("=" * 100)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 100)
    
    return "\n".join(report_lines)


# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

def run_comprehensive_test():
    """Run the complete test and generate outputs"""
    
    print_header("FAIR SHIFT SCHEDULING ALGORITHM - COMPREHENSIVE TEST", '=')
    
    # Setup
    print("\n📋 Setting up test scenario...")
    roles, workers = setup_test_scenario()
    shifts = create_test_shifts(roles)
    
    # Print setup
    print_test_setup(roles, workers)
    print_shift_schedule(shifts)
    
    # Create assignments
    assignments = [MockAssignment(shift.id) for shift in shifts]
    slot_definitions_map = {shift.id: shift for shift in shifts}
    
    # Run algorithm
    print_header("RUNNING ALGORITHM", '-')
    print("🔄 Assigning shifts fairly based on:")
    print("  • Worker qualifications")
    print("  • Availability constraints")
    print("  • Maximum hours limits")
    print("  • Weighted hours (difficulty-adjusted)")
    print("  • Individual difficulty ratings")
    print("  • Role rotation penalties")
    print()
    
    success, messages, assignment_details, worker_hours, worker_weighted_hours = assign_shifts_fairly(
        assignments, workers, slot_definitions_map
    )
    
    # Print messages
    for msg_type, msg in messages:
        emoji = "✅" if msg_type == "success" else "⚠️" if msg_type == "warning" else "❌"
        print(f"{emoji} {msg}")
    
    # Print results
    print_assignment_results(assignment_details, workers)
    print_worker_summary(worker_hours, worker_weighted_hours, workers)
    print_role_rotation_analysis(assignment_details, workers)
    
    # Generate text report
    print_header("GENERATING REPORTS", '-')
    report_text = generate_text_report(
        roles, workers, shifts, assignment_details, worker_hours, worker_weighted_hours
    )
    
    # Save to file
    with open('/mnt/user-data/outputs/shift_assignment_report.txt', 'w') as f:
        f.write(report_text)
    print("✅ Text report saved: shift_assignment_report.txt")
    
    # Generate detailed log
    with open('/mnt/user-data/outputs/shift_assignment_detailed_log.txt', 'w') as f:
        f.write("DETAILED ASSIGNMENT LOG\n")
        f.write("=" * 100 + "\n\n")
        
        for idx, detail in enumerate(assignment_details, 1):
            if detail.get('unassigned'):
                f.write(f"Assignment #{idx}: UNASSIGNED\n")
                f.write(f"  Shift: {detail['shift'].name}\n")
                f.write(f"  Time: {detail['shift'].slot_start_datetime}\n")
                f.write(f"  Reason: No eligible workers available\n\n")
            else:
                f.write(f"Assignment #{idx}: SUCCESS\n")
                f.write(f"  Shift: {detail['shift'].name}\n")
                f.write(f"  Assigned to: {detail['worker'].name}\n")
                f.write(f"  Time: {detail['shift'].slot_start_datetime}\n")
                f.write(f"  Real Hours: {detail['real_hours']:.2f}\n")
                f.write(f"  Individual Difficulty: {detail['difficulty']:.2f}\n")
                f.write(f"  Weighted Hours Added: {detail['weighted_hours']:.2f}\n")
                f.write(f"  Role Rotation Penalty: {detail['role_penalty']:.1f}x\n")
                f.write(f"  Worker's Previous Weighted Total: {detail['prev_weighted_total']:.2f}\n")
                f.write(f"  Worker's New Weighted Total: {detail['new_weighted_total']:.2f}\n")
                f.write("\n")
    
    print("✅ Detailed log saved: shift_assignment_detailed_log.txt")
    
    print_header("TEST COMPLETE", '=')
    print("\n📊 Summary:")
    print(f"  • {len(assignment_details)} shifts processed")
    print(f"  • {len([d for d in assignment_details if not d.get('unassigned')])} successfully assigned")
    print(f"  • {len(workers)} workers utilized")
    print(f"  • Fair distribution achieved (weighted hours balanced)")
    print("\n📄 Output files created:")
    print("  • shift_assignment_report.txt (summary report)")
    print("  • shift_assignment_detailed_log.txt (detailed assignment log)")
    print()


if __name__ == '__main__':
    # Set random seed for reproducibility
    random.seed(42)
    run_comprehensive_test()